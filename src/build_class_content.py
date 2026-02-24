#!/usr/bin/env python3
"""Build GH2E class objects (single-class + multi-class content pack).

Usage:
  python3 src/build_class_content.py single --class-id silent_knife
  python3 src/build_class_content.py single --class-id bruiser
  python3 src/build_class_content.py pack --class-ids silent_knife,bruiser
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any

import build_skeleton


RAW_BASE = "https://raw.githubusercontent.com/Fusdahl/gloomhaven2e-tts-support/main/assets/"

CONTENT_BOX_MESH_REL = "final_class_models/content_box_source/content_box_mesh.obj"
CONTENT_BOX_DIFFUSE_REL = "final_class_models/content_box_source/content_box_diffuse.png"
CONTENT_BOX_ICON_REL = "final_class_models/content_box_source/content_icon.png"

SCOUNDREL_SOURCE_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "saved objects for working 1st class" / "Scoundrel  working 1st edition.json",
    Path(__file__).resolve().parent.parent / "saved objects for working 1st class" / "Scoundrel  top box.json",
]

DEFAULT_PERK_POSITIONS = [
    (80, 322),
    (80, 286),
    (80, 253),
    (105, 253),
    (128, 253),
    (80, 200),
    (105, 200),
    (128, 200),
    (80, 71),
    (105, 71),
    (80, 11),
    (105, 11),
    (80, -51),
    (105, -51),
    (80, -86),
    (80, -241),
    (80, -390),
    (80, -408),
]
DEFAULT_MASTERY_POSITIONS = [(-336, -339), (-336, -430)]

DROP_OBJECT_NICKNAMES = {"decorative crate"}
WHITE_DIFFUSE = {"r": 1.0, "g": 1.0, "b": 1.0}

_SCOUNDREL_FIGURE_TEMPLATE_CACHE: dict[str, Any] | None = None


def _normalize_spaces(text: str) -> str:
    return text.replace("\u00A0", " ")


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_spaces(text)).strip().lower()


def _slug_to_display_name(slug: str) -> str:
    special = {"tricksters": "Trickster's", "duelists": "Duelist's"}
    parts = slug.split("-")
    out_parts: list[str] = []
    for part in parts:
        if part in special:
            out_parts.append(special[part])
        else:
            out_parts.append(part.capitalize())
    return " ".join(out_parts)


def _strip_initiative_suffix(name: str) -> str:
    return re.sub(r"\s*\(\d+\)\s*$", "", name).strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _to_asset_url(rel_path: str, asset_rev: str) -> str:
    return RAW_BASE + rel_path + f"?v={asset_rev}"


def _find_first_by_guid(node: Any, guid: str) -> dict[str, Any] | None:
    if isinstance(node, dict):
        if node.get("GUID") == guid:
            return node
        for value in node.values():
            found = _find_first_by_guid(value, guid)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_by_guid(item, guid)
            if found is not None:
                return found
    return None


def _find_first_by_nickname(node: Any, nickname: str) -> dict[str, Any] | None:
    if isinstance(node, dict):
        if node.get("Nickname") == nickname:
            return node
        for value in node.values():
            found = _find_first_by_nickname(value, nickname)
            if found is not None:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _find_first_by_nickname(item, nickname)
            if found is not None:
                return found
    return None


def _iter_objects(node: Any):
    if isinstance(node, dict):
        if "Name" in node and "GUID" in node:
            yield node
        for value in node.values():
            yield from _iter_objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_objects(item)


def _collect_guid_counts(node: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for obj in _iter_objects(node):
        guid = obj.get("GUID")
        if isinstance(guid, str):
            counts[guid] = counts.get(guid, 0) + 1
    return counts


def _dedupe_guids(node: Any) -> int:
    used = build_skeleton.collect_guids(node)
    seen: set[str] = set()
    changed = 0

    def walk(obj: Any) -> None:
        nonlocal changed
        if isinstance(obj, dict):
            guid = obj.get("GUID")
            if isinstance(guid, str):
                if guid in seen:
                    obj["GUID"] = build_skeleton.random_guid(used)
                    changed += 1
                else:
                    seen.add(guid)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(node)
    return changed


def _load_scoundrel_figure_template() -> dict[str, Any]:
    global _SCOUNDREL_FIGURE_TEMPLATE_CACHE
    if _SCOUNDREL_FIGURE_TEMPLATE_CACHE is not None:
        return _SCOUNDREL_FIGURE_TEMPLATE_CACHE

    source_file = next((p for p in SCOUNDREL_SOURCE_CANDIDATES if p.exists()), None)
    if source_file is None:
        joined = ", ".join(str(p) for p in SCOUNDREL_SOURCE_CANDIDATES)
        raise RuntimeError(f"Missing Scoundrel source file. Checked: {joined}")

    source = _load_json(source_file)
    root = source
    if isinstance(source, dict) and isinstance(source.get("ObjectStates"), list) and source["ObjectStates"]:
        root = source["ObjectStates"][0]

    figure = _find_first_by_guid(root, "scoundrel-figure")
    if not isinstance(figure, dict):
        raise RuntimeError("Could not find scoundrel-figure in Scoundrel source object")

    _SCOUNDREL_FIGURE_TEMPLATE_CACHE = figure
    return figure


def _load_profiles(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = _load_json(path)
    if not isinstance(raw, dict):
        raise RuntimeError(f"Invalid profiles JSON: {path}")
    classes = raw.get("classes")
    if not isinstance(classes, dict):
        raise RuntimeError(f"Missing 'classes' map in: {path}")
    return raw, classes


def _resolve_profile(global_cfg: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    p = copy.deepcopy(profile)
    class_id = p["class_id"]
    class_name = p["class_name"]
    asset_rev = global_cfg.get("asset_rev", "r0")

    class_id_prefix = f"gh2e-{class_id.replace('_', '-')}"
    class_bag_guid = f"{class_id_prefix}-box"
    class_small_guid = f"{class_id_prefix}-small-box"
    class_icon_name = p.get("class_icon_name") or f"{class_name.replace(' ', '_')}_Icon"

    def url_from_rel(rel: str | None) -> str | None:
        if not rel:
            return None
        return _to_asset_url(rel, asset_rev)

    model_source_dir = p["model_source_dir"]
    top_model_source_dir = p.get("top_model_source_dir") or model_source_dir
    class_icon_rel = p.get("class_icon_path") or f"final_class_models/{model_source_dir}/class_icon.png"

    resolved = {
        **p,
        "asset_rev": asset_rev,
        "class_id_prefix": class_id_prefix,
        "class_bag_guid": class_bag_guid,
        "class_small_guid": class_small_guid,
        "class_icon_name": class_icon_name,
        "legacy_class_bag_guid": p.get("legacy_class_bag_guid", "gh2e-spears-big-box"),
        "legacy_small_box_guid": p.get("legacy_small_box_guid", "gh2e-spears-small-box"),
        "legacy_id_prefix": p.get("legacy_id_prefix", "gh2e-spears"),
        "template_aliases": p.get("template_aliases", ["Quartermaster", "Three Spears", "Scoundrel"]),
        "perk_positions": [tuple(x) for x in p.get("perk_positions", DEFAULT_PERK_POSITIONS)],
        "mastery_positions": [tuple(x) for x in p.get("mastery_positions", DEFAULT_MASTERY_POSITIONS)],
        "ability_face_url": url_from_rel(p.get("ability_face_path")),
        "ability_back_url": url_from_rel(p.get("ability_back_path")),
        "ability_num_width": int(p.get("ability_num_width", 8)),
        "ability_num_height": int(p.get("ability_num_height", 4)),
        "amd_face_url": url_from_rel(p.get("amd_face_path")),
        "amd_back_url": url_from_rel(p.get("amd_back_path")),
        "extra_face_url": url_from_rel(p.get("extra_face_path")),
        "extra_back_url": url_from_rel(p.get("extra_back_path")),
        "sheet_front_url": url_from_rel(p.get("sheet_front_path")),
        "sheet_back_url": url_from_rel(p.get("sheet_back_path")),
        "character_mat_url": url_from_rel(p.get("character_mat_path")),
        "content_box_mesh_url": _to_asset_url(CONTENT_BOX_MESH_REL, asset_rev),
        "content_box_diffuse_url": _to_asset_url(CONTENT_BOX_DIFFUSE_REL, asset_rev),
        "content_box_icon_url": _to_asset_url(CONTENT_BOX_ICON_REL, asset_rev),
        "class_top_box_mesh_url": _to_asset_url(f"final_class_models/{top_model_source_dir}/class_top_box_mesh.obj", asset_rev),
        "class_top_box_diffuse_url": _to_asset_url(
            f"final_class_models/{top_model_source_dir}/class_top_box_diffuse.png", asset_rev
        ),
        "class_top_box_icon_url": url_from_rel(p.get("class_top_box_icon_path")) or _to_asset_url(class_icon_rel, asset_rev),
        "class_box_mesh_url": _to_asset_url(f"final_class_models/{model_source_dir}/class_box_mesh.obj", asset_rev),
        "class_box_diffuse_url": _to_asset_url(f"final_class_models/{model_source_dir}/class_box_diffuse.png", asset_rev),
        "class_icon_url": _to_asset_url(class_icon_rel, asset_rev),
        "box_mask_front_url": _to_asset_url(f"final_class_models/{model_source_dir}/character_box_mask_front.png", asset_rev),
        "box_mask_side_url": _to_asset_url(f"final_class_models/{model_source_dir}/character_box_mask_side.png", asset_rev),
        "figure_assetbundle_url": None,
        "figure_mesh_url": None,
        "figure_diffuse_url": None,
        "figure_normal_url": None,
    }

    base = Path(__file__).resolve().parent.parent / "assets" / "final_class_models" / model_source_dir
    if (base / "class_figure.unity3d").exists():
        resolved["figure_assetbundle_url"] = _to_asset_url(f"final_class_models/{model_source_dir}/class_figure.unity3d", asset_rev)
    elif (base / "class_figure_mesh.obj").exists():
        resolved["figure_mesh_url"] = _to_asset_url(f"final_class_models/{model_source_dir}/class_figure_mesh.obj", asset_rev)
        if (base / "class_figure_diffuse.png").exists():
            resolved["figure_diffuse_url"] = _to_asset_url(f"final_class_models/{model_source_dir}/class_figure_diffuse.png", asset_rev)
        if (base / "class_figure_normal.png").exists():
            resolved["figure_normal_url"] = _to_asset_url(f"final_class_models/{model_source_dir}/class_figure_normal.png", asset_rev)
    return resolved


def _parse_ability_entries(profile: dict[str, Any]) -> list[dict[str, Any]]:
    order_file = Path(profile["ability_order_file"])
    if not order_file.exists():
        raise RuntimeError(f"Missing ability order file: {order_file}")

    entries: list[dict[str, Any]] = []
    lines = order_file.read_text(encoding="utf-8").splitlines()
    card_base = int(profile.get("ability_card_base", 345299))
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("|")
        if len(parts) != 4:
            continue
        idx_raw, level_raw, init_raw, filename = parts
        idx = int(idx_raw)
        level = level_raw.strip()
        initiative = int(init_raw)
        slug = filename.rsplit(".", 1)[0]
        entries.append(
            {
                "idx": idx,
                "card_id": card_base + idx,
                "name": _slug_to_display_name(slug),
                "level": level,
                "initiative": initiative,
            }
        )
    entries.sort(key=lambda x: x["idx"])

    expected = profile.get("expected_ability_count")
    if expected is not None and len(entries) != int(expected):
        raise RuntimeError(f"Expected {expected} ability entries for {profile['class_id']}, got {len(entries)}")
    if not entries:
        raise RuntimeError(f"No ability entries parsed from {order_file}")
    return entries


def _compute_ability_deck_ids(entries: list[dict[str, Any]]) -> tuple[list[int], list[int]]:
    start = [e["card_id"] for e in entries if str(e["level"]).upper() in {"1", "X"}]
    advanced = [e["card_id"] for e in entries if str(e["level"]).upper() not in {"1", "X"}]
    return sorted(start, reverse=True), sorted(advanced, reverse=True)


def _build_abilities_lua_block(entries: list[dict[str, Any]]) -> str:
    lines = ["  abilities = {"]
    for entry in entries:
        level = entry["level"]
        level_lua = '"X"' if str(level).upper() == "X" else str(int(level))
        lines.append(f'    ["{entry["name"]}"] = {{')
        lines.append(f"      level = {level_lua},")
        lines.append(f'      initiative = {entry["initiative"]},')
        lines.append("    },")
    lines.append("  }")
    return "\n".join(lines)


def _patch_figure_lua_starting_health(lua_script: str, hp_start: int) -> str:
    if not lua_script:
        return lua_script
    return re.sub(r"startingHealth\s*=\s*\d+", f"startingHealth = {hp_start}", lua_script, count=1)


def _contains_class_lua(lua_script: str) -> bool:
    return "ClassApi.registerClass(" in lua_script and "perks" in lua_script and "abilities" in lua_script


def _build_single_base_object(global_cfg: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    source_mod = build_skeleton.load_json(Path(global_cfg["source_mod"]))
    class_data = {"class_name": profile["class_name"]}
    single_object = build_skeleton.build_single_object(
        source_mod,
        class_data,
        image_url=None,
        regenerate_class_guids=False,
        rename_internal_class_identity=True,
    )
    return build_skeleton.wrap_as_save(single_object, profile["class_name"])


def _resolve_source_saved_object(profile: dict[str, Any]) -> Path | None:
    rel = profile.get("source_saved_object")
    if not isinstance(rel, str) or not rel.strip():
        return None
    path = Path(__file__).resolve().parent.parent / rel
    return path if path.exists() else None


def _extract_root_state(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("ObjectStates"), list) and data["ObjectStates"]:
        root = data["ObjectStates"][0]
        if isinstance(root, dict):
            return root
    return data


def _source_class_name(profile: dict[str, Any]) -> str:
    name = profile.get("source_class_name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return profile["class_name"]


def _extract_summons_bag_from_source(profile: dict[str, Any]) -> dict[str, Any] | None:
    source_path = _resolve_source_saved_object(profile)
    if source_path is None:
        return None
    source = _load_json(source_path)
    root = _extract_root_state(source)
    for obj in _iter_objects(root):
        if obj.get("Name") == "Bag" and _normalize_key(obj.get("Nickname", "")) == "summons":
            return copy.deepcopy(obj)
    return None


def _extract_attack_modifiers_from_source(profile: dict[str, Any]) -> dict[str, Any] | None:
    source_path = _resolve_source_saved_object(profile)
    if source_path is None:
        return None
    source = _load_json(source_path)
    root = _extract_root_state(source)
    class_name = _source_class_name(profile)

    source_class_box = None
    for obj in _iter_objects(root):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            source_class_box = obj
            break
    if not isinstance(source_class_box, dict):
        return None

    for child in source_class_box.get("ContainedObjects", []) or []:
        if isinstance(child, dict) and _normalize_key(child.get("Nickname", "")) == "attack modifiers":
            return copy.deepcopy(child)
    return None


def _extract_source_summon_card_scripts(profile: dict[str, Any]) -> dict[str, str]:
    source_path = _resolve_source_saved_object(profile)
    if source_path is None:
        return {}
    source = _load_json(source_path)
    root = _extract_root_state(source)
    scripts: dict[str, str] = {}
    for obj in _iter_objects(root):
        if obj.get("Name") != "Card":
            continue
        lua = obj.get("LuaScript")
        nick = obj.get("Nickname")
        if not isinstance(lua, str) or not lua.strip():
            continue
        if "SummonCard.forSummon(" not in lua:
            continue
        if not isinstance(nick, str) or not nick.strip():
            continue
        key = _normalize_key(_strip_initiative_suffix(nick))
        scripts[key] = lua
    return scripts


SUMMON_CARD_POSITIONS = ("SummonCard.Position.FHTop", "SummonCard.Position.FHBottom")


def _normalize_summon_card_position(value: str | None, index: int) -> str:
    if isinstance(value, str) and value.strip():
        token = value.strip()
        if token.startswith("SummonCard.Position."):
            return token
        return f"SummonCard.Position.{token}"
    return SUMMON_CARD_POSITIONS[index % len(SUMMON_CARD_POSITIONS)]


def _expand_spawn_only_summon_spec(spec: Any) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []

    if isinstance(spec, str) and spec.strip():
        entries.append((spec.strip(), SUMMON_CARD_POSITIONS[0]))
        return entries

    if isinstance(spec, list):
        for item in spec:
            entries.extend(_expand_spawn_only_summon_spec(item))
        return entries

    if not isinstance(spec, dict):
        return entries

    name = spec.get("name")
    if not isinstance(name, str) or not name.strip():
        return entries
    summon_name = name.strip()

    positions_raw = spec.get("positions")
    positions: list[str] = []
    if isinstance(positions_raw, list):
        for i, raw in enumerate(positions_raw):
            if isinstance(raw, str):
                positions.append(_normalize_summon_card_position(raw, i))

    count_raw = spec.get("count", len(positions) if positions else 1)
    try:
        count = int(count_raw)
    except (TypeError, ValueError):
        count = 1
    count = max(1, count)

    for i in range(count):
        position = positions[i] if i < len(positions) else _normalize_summon_card_position(None, i)
        entries.append((summon_name, position))
    return entries


def _patch_summon_card_lua_spawn_only(lua_script: str, entries: list[tuple[str, str]]) -> str:
    if not isinstance(lua_script, str) or not lua_script or not entries:
        return lua_script

    require_marker = 'local SummonCard = require("Component.SummonCard")'
    component_marker = '__bundle_register("Component.SummonCard"'
    component_idx = lua_script.find(component_marker)
    if component_idx < 0:
        return lua_script

    before = lua_script[:component_idx]
    after = lua_script[component_idx:]
    lines = before.splitlines(keepends=True)
    require_line_idx = None
    for i, line in enumerate(lines):
        if require_marker in line:
            require_line_idx = i
            break
    if require_line_idx is None:
        return lua_script

    filtered = [line for line in lines if "SummonCard.forSummon(" not in line]
    call_lines = [f"SummonCard.forSummon({json.dumps(name)}, {position})\n" for name, position in entries]
    rebuilt = (
        filtered[: require_line_idx + 1]
        + ["\n"]
        + call_lines
        + ["\n"]
        + filtered[require_line_idx + 1 :]
    )
    return "".join(rebuilt) + after


def _extract_source_class_child_by_nickname(profile: dict[str, Any], nickname: str) -> dict[str, Any] | None:
    source_path = _resolve_source_saved_object(profile)
    if source_path is None:
        return None
    source = _load_json(source_path)
    root = _extract_root_state(source)
    class_name = _source_class_name(profile)
    source_class_box = None
    for obj in _iter_objects(root):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            source_class_box = obj
            break
    if not isinstance(source_class_box, dict):
        return None
    for child in source_class_box.get("ContainedObjects", []) or []:
        if isinstance(child, dict) and _normalize_key(child.get("Nickname", "")) == _normalize_key(nickname):
            return copy.deepcopy(child)
    return None


def _ensure_source_class_children(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    names = profile.get("source_class_objects")
    if not isinstance(names, list) or not names:
        return
    class_name = profile["class_name"]
    class_box = None
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            class_box = obj
            break
    if not isinstance(class_box, dict):
        return
    contained = class_box.get("ContainedObjects")
    if not isinstance(contained, list):
        return

    existing = {
        _normalize_key(o.get("Nickname", ""))
        for o in contained
        if isinstance(o, dict) and isinstance(o.get("Nickname"), str)
    }
    used_guids = build_skeleton.collect_guids(root_data)
    for raw_name in names:
        if not isinstance(raw_name, str) or not raw_name.strip():
            continue
        key = _normalize_key(raw_name)
        if key in existing:
            continue
        child = _extract_source_class_child_by_nickname(profile, raw_name)
        if not isinstance(child, dict):
            continue
        build_skeleton.regenerate_guids(child, seen=used_guids)
        contained.append(child)
        existing.add(key)


def _remap_summon_asset_urls(summons_bag: dict[str, Any], profile: dict[str, Any]) -> None:
    model_source_dir = profile["model_source_dir"]
    asset_rev = profile["asset_rev"]
    summon_dir = Path(__file__).resolve().parent.parent / "assets" / "final_class_models" / model_source_dir / "summons"
    if not summon_dir.exists():
        return

    mesh_files = sorted(summon_dir.glob("*mesh*.obj"))
    diffuse_files = sorted(summon_dir.glob("*diffuse*.png"))
    mesh_url = _to_asset_url(f"final_class_models/{model_source_dir}/summons/{mesh_files[0].name}", asset_rev) if mesh_files else None
    diffuse_urls = [_to_asset_url(f"final_class_models/{model_source_dir}/summons/{p.name}", asset_rev) for p in diffuse_files]

    contained = summons_bag.get("ContainedObjects")
    if not isinstance(contained, list):
        return

    model_index = 0
    for obj in contained:
        if not isinstance(obj, dict):
            continue
        custom_mesh = obj.get("CustomMesh")
        if not isinstance(custom_mesh, dict):
            continue
        if mesh_url:
            custom_mesh["MeshURL"] = mesh_url
        if model_index < len(diffuse_urls):
            custom_mesh["DiffuseURL"] = diffuse_urls[model_index]
        # Avoid external dependencies; TTS can use mesh for collider if URL is empty.
        custom_mesh["ColliderURL"] = ""
        model_index += 1


def _format_lua_scalar(value: Any) -> str:
    if isinstance(value, str):
        return '"' + value.replace('"', '\\"') + '"'
    return str(value)


def _patch_summon_lua_stats(lua_script: str, override: dict[str, Any]) -> str:
    if not lua_script or not isinstance(override, dict):
        return lua_script

    block_match = re.search(r"stats\s*=\s*\{.*?\n\}", lua_script, flags=re.S)
    if not block_match:
        return lua_script

    block = block_match.group(0)
    patched = block

    if "health" in override:
        patched = re.sub(
            r"(\bhealth\s*=\s*)(\"[^\"]*\"|-?\d+)(\s*,)",
            rf"\g<1>{_format_lua_scalar(override['health'])}\g<3>",
            patched,
            count=1,
        )

    if "movement" in override:
        patched = re.sub(
            r"(\bmovement\s*=\s*)(\"[^\"]*\"|-?\d+)(\s*,)",
            rf"\g<1>{_format_lua_scalar(override['movement'])}\g<3>",
            patched,
            count=1,
        )

    if "range" in override:
        patched = re.sub(
            r"(\brange\s*=\s*)(\"[^\"]*\"|-?\d+)(\s*,)",
            rf"\g<1>{_format_lua_scalar(override['range'])}\g<3>",
            patched,
            count=1,
        )

    if "attack" in override:
        attack_value = _format_lua_scalar(override["attack"])
        if re.search(r"\battack\s*=\s*\{", patched):
            patched = re.sub(
                r"(\battack\s*=\s*\{.*?\bvalue\s*=\s*)(\"[^\"]*\"|-?\d+)(\s*,)",
                rf"\g<1>{attack_value}\g<3>",
                patched,
                count=1,
                flags=re.S,
            )
        else:
            patched = re.sub(
                r"(\battack\s*=\s*)(\"[^\"]*\"|-?\d+)(\s*,)",
                rf"\g<1>{attack_value}\g<3>",
                patched,
                count=1,
            )

    if patched == block:
        return lua_script
    return lua_script[: block_match.start()] + patched + lua_script[block_match.end() :]


def _apply_summon_stats_overrides(summons_bag: dict[str, Any], profile: dict[str, Any]) -> None:
    overrides = profile.get("summon_stats")
    if not isinstance(overrides, dict):
        return
    contained = summons_bag.get("ContainedObjects")
    if not isinstance(contained, list):
        return
    for summon in contained:
        if not isinstance(summon, dict):
            continue
        nickname = summon.get("Nickname")
        if not isinstance(nickname, str):
            continue
        override = overrides.get(nickname)
        if not isinstance(override, dict):
            continue
        lua = summon.get("LuaScript")
        if isinstance(lua, str) and lua:
            summon["LuaScript"] = _patch_summon_lua_stats(lua, override)


def _sync_summon_roster(root_data: dict[str, Any], summons_bag: dict[str, Any], profile: dict[str, Any]) -> None:
    names = profile.get("summon_names")
    if not isinstance(names, list) or not names:
        return
    desired = [str(x).strip() for x in names if isinstance(x, str) and x.strip()]
    if not desired:
        return
    contained = summons_bag.get("ContainedObjects")
    if not isinstance(contained, list) or not contained:
        return

    summon_objs = [o for o in contained if isinstance(o, dict)]
    if not summon_objs:
        return
    template = summon_objs[0]
    model_aliases = profile.get("summon_model_aliases", {})
    if not isinstance(model_aliases, dict):
        model_aliases = {}

    used_guids = build_skeleton.collect_guids(root_data)
    pool: list[dict[str, Any]] = summon_objs[:]
    selected: list[dict[str, Any]] = []
    for name in desired:
        wanted_keys = [_normalize_key(name)]
        alias = model_aliases.get(name)
        if isinstance(alias, str) and alias.strip():
            wanted_keys.append(_normalize_key(alias))
        pick_idx = None
        for idx, obj in enumerate(pool):
            nick = obj.get("Nickname")
            if isinstance(nick, str) and _normalize_key(nick) in wanted_keys:
                pick_idx = idx
                break
        if pick_idx is not None:
            selected.append(pool.pop(pick_idx))
        elif pool:
            selected.append(pool.pop(0))
        else:
            clone = copy.deepcopy(template)
            build_skeleton.regenerate_guids(clone, seen=used_guids)
            selected.append(clone)

    for idx, name in enumerate(desired):
        selected[idx]["Nickname"] = name

    summons_bag["ContainedObjects"] = selected


def _ensure_class_summons(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    class_name = profile["class_name"]
    class_box = None
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            class_box = obj
            break
    if not isinstance(class_box, dict):
        return
    contained = class_box.get("ContainedObjects")
    if not isinstance(contained, list):
        return
    for child in contained:
        if isinstance(child, dict) and child.get("Name") == "Bag" and _normalize_key(child.get("Nickname", "")) == "summons":
            _sync_summon_roster(root_data, child, profile)
            # Summons already present; still remap assets in case URLs are stale.
            if profile.get("remap_summon_assets", True):
                _remap_summon_asset_urls(child, profile)
            _apply_summon_stats_overrides(child, profile)
            return

    summons_bag = _extract_summons_bag_from_source(profile)
    if not isinstance(summons_bag, dict):
        return
    _sync_summon_roster(root_data, summons_bag, profile)
    if profile.get("remap_summon_assets", True):
        _remap_summon_asset_urls(summons_bag, profile)
    _apply_summon_stats_overrides(summons_bag, profile)

    used_guids = build_skeleton.collect_guids(root_data)
    build_skeleton.regenerate_guids(summons_bag, seen=used_guids)
    contained.append(summons_bag)


def _collect_class_summon_defs(root_data: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, str]]:
    class_name = profile["class_name"]
    class_box = None
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            class_box = obj
            break
    if not isinstance(class_box, dict):
        return []
    contained = class_box.get("ContainedObjects")
    if not isinstance(contained, list):
        return []
    summons_bag = next(
        (o for o in contained if isinstance(o, dict) and o.get("Name") == "Bag" and _normalize_key(o.get("Nickname", "")) == "summons"),
        None,
    )
    if not isinstance(summons_bag, dict):
        return []

    defs: list[dict[str, str]] = []
    for summon in summons_bag.get("ContainedObjects", []) or []:
        if not isinstance(summon, dict):
            continue
        name = summon.get("Nickname")
        if not isinstance(name, str) or not name.strip():
            continue
        custom_mesh = summon.get("CustomMesh")
        if not isinstance(custom_mesh, dict):
            continue
        image = custom_mesh.get("DiffuseURL")
        if not isinstance(image, str) or not image.strip():
            continue
        defs.append({"name": name.strip(), "image": image.strip()})
    return defs


def _replace_attack_modifiers_from_source(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    if not profile.get("use_source_attack_modifiers"):
        return
    class_name = profile["class_name"]
    class_box = None
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            class_box = obj
            break
    if not isinstance(class_box, dict):
        return

    source_amd = _extract_attack_modifiers_from_source(profile)
    if not isinstance(source_amd, dict):
        return

    contained = class_box.get("ContainedObjects")
    if not isinstance(contained, list):
        return
    for idx, child in enumerate(contained):
        if isinstance(child, dict) and _normalize_key(child.get("Nickname", "")) == "attack modifiers":
            source_amd["Transform"] = child.get("Transform", source_amd.get("Transform"))
            contained[idx] = source_amd
            return
    contained.append(source_amd)


def _patch_outer_lua_summon_registration(lua_script: str, summon_defs: list[dict[str, str]]) -> str:
    if not lua_script:
        return lua_script

    out = re.sub(r"\r?\n\s*--\s*ContentApi\.registerSummon\(\{[^\n]*\}\)", "", lua_script)
    out = re.sub(r"\r?\n\s*ContentApi\.registerSummon\(\{[^\n]*\}\)", "", out)

    if summon_defs:
        block_lines = ["  --summon registration"]
        for summon in summon_defs:
            name = summon["name"].replace('"', '\\"')
            image = summon["image"].replace('"', '\\"')
            block_lines.append(f'  ContentApi.registerSummon({{ name = "{name}", image = "{image}"}})')
        block = "\n".join(block_lines)
    else:
        block = "  --summon registration"

    marker = "  --solo scenario registration"
    if marker in out:
        out = re.sub(
            r"(  --summon registration\s*)(.*?)(?=\r?\n\s*  --solo scenario registration)",
            block,
            out,
            count=1,
            flags=re.S,
        )
        if block not in out:
            out = out.replace(marker, block + "\n\n" + marker, 1)
    else:
        out = out.replace("end\n\nend)", block + "\nend\n\nend)", 1)
    return out


def _ensure_outer_class_summon_registration(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    summon_defs = _collect_class_summon_defs(root_data, profile)
    if not summon_defs:
        return
    class_name = profile["class_name"]
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Infinite_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            lua = obj.get("LuaScript")
            if isinstance(lua, str):
                obj["LuaScript"] = _patch_outer_lua_summon_registration(lua, summon_defs)
            break


def _remove_class_summons(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    class_name = profile["class_name"]
    class_box = None
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            class_box = obj
            break
    if not isinstance(class_box, dict):
        return
    contained = class_box.get("ContainedObjects")
    if not isinstance(contained, list):
        return
    class_box["ContainedObjects"] = [
        child
        for child in contained
        if not (isinstance(child, dict) and child.get("Name") == "Bag" and _normalize_key(child.get("Nickname", "")) == "summons")
    ]


def _clear_outer_class_summon_registration(root_data: dict[str, Any], profile: dict[str, Any]) -> None:
    class_name = profile["class_name"]
    for obj in _iter_objects(root_data):
        if obj.get("Name") == "Custom_Model_Infinite_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            lua = obj.get("LuaScript")
            if isinstance(lua, str):
                obj["LuaScript"] = _patch_outer_lua_summon_registration(lua, [])
            break


def _patch_character_sheet_lua(lua_script: str, profile: dict[str, Any]) -> str:
    perk_lines = "\n".join(f"    {{ {x} , {y} }}," for x, y in profile["perk_positions"])
    mastery_lines = "\n".join(f"    {{ {x} , {y} }}," for x, y in profile["mastery_positions"])

    perk_pattern = re.compile(
        r"(  -- Positions of the perks\s+  perkPositions = \{\s+)(.*?)(\s+  \},\s+  -- Positions of the masteries)",
        re.S,
    )
    mastery_pattern = re.compile(
        r"(  -- Positions of the masteries\s+  masteryPositions = \{\s+)(.*?)(\s+  \},\s+\}\))",
        re.S,
    )

    patched = perk_pattern.sub(rf"\1{perk_lines}\3", lua_script, count=1)
    patched = mastery_pattern.sub(rf"\1{mastery_lines}\3", patched, count=1)

    patched = patched.replace("  this.onChangeLevel = function(_, value, element)", "  this.onChangeLevel = function(player, value, element)", 1)
    patched = patched.replace(
        "    CharacterApi.setLevel(this.player, newLevel)",
        """    local targetPlayer = this.player or (player and player.color) or player
    if targetPlayer ~= nil then
      this.player = targetPlayer
      pcall(CharacterApi.setLevel, targetPlayer, newLevel)
    end""",
        1,
    )
    patched = patched.replace("  this.onPerkClicked = function(_, value, element)", "  this.onPerkClicked = function(player, value, element)", 1)
    patched = re.sub(
        r"(this\.onPerkClicked = function\(player, value, element\)\s+)(local perk = Ui\.getIndex\(element\.id, \"_\(.\*\)\"\)\s+self\.data\.perks\[perk\] = value)",
        r"""\1if element == nil or element.id == nil then
      return
    end
    local perk = Ui.getIndex(element.id, "_(.*)")
    if perk == nil then
      return
    end
    self.data.perks[perk] = value""",
        patched,
        count=1,
        flags=re.S,
    )
    patched = patched.replace("    CharacterApi.changePerk(this.player, perk, value)", "    -- Intentionally no CharacterApi perk sync for local test build.", 1)
    patched = patched.replace("    this.initUi()", '    ttsSelf.UI.setXml("")\n    this.initUi()', 1)
    patched = re.sub(
        r"this\.player = ComponentApi\.getOwner\(ttsSelf\)\s+ExtensionApi\.registerExtensions\(\)\s+ttsSelf\.UI\.setXml\(\"\"\)\s+this\.initUi\(\)",
        """this.player = ComponentApi.getOwner(ttsSelf)
    ExtensionApi.registerExtensions()

    if this.player == nil then
      ttsSelf.UI.setXml("")
      this.initUi()
    else
      Wait.time(function()
        if ttsSelf.UI.getXml() == "" then
          ttsSelf.UI.setXml("")
          this.initUi()
        end
      end, 0.5)
    end""",
        patched,
        count=1,
        flags=re.S,
    )
    patched = patched.replace("  function this.initUi()", '  function this.initUi()\n    ttsSelf.UI.setXml("")', 1)
    return patched


def _make_text_patcher(profile: dict[str, Any]):
    aliases = profile["template_aliases"]
    class_name = profile["class_name"]
    class_icon_name = profile["class_icon_name"]

    def patch_text_value(text: str) -> str:
        out = _normalize_spaces(text)
        for alias in aliases:
            out = out.replace(alias, class_name)
            out = out.replace(alias.replace(" ", "\u00A0"), class_name)
            out = out.replace(alias.replace(" ", "") + "_Icon", class_icon_name)
            out = out.replace(alias + "_Icon", class_icon_name)
            out = out.replace(alias + " _Icon", class_icon_name)
        out = re.sub(r"\s+", " ", out).strip()
        return out

    return patch_text_value


def _patch_outer_class_lua(lua_script: str, profile: dict[str, Any], ability_entries: list[dict[str, Any]]) -> str:
    class_name = profile["class_name"]
    hp_values = profile["hp"]
    class_icon_url = profile["class_icon_url"]

    patched = re.sub(r'ClassApi\.registerClass\("([^"]+)"', f'ClassApi.registerClass("{class_name}"', lua_script, count=1)
    hp_block = "hp = {\n" + "".join(f"    {value},\n" for value in hp_values) + "  },"
    patched = re.sub(r"hp\s*=\s*\{\s*[\d,\s]*\s*\},", hp_block, patched, count=1, flags=re.S)
    patched = re.sub(
        r"extra\s*=\s*\{\s*\{\s*name\s*=\s*\"Decorative crate\"\s*,\s*target\s*=\s*\"PlayerMat\"\s*,\s*\}\s*,\s*\{\s*name\s*=\s*\"[^\"]*Personal Supply\"\s*,\s*target\s*=\s*\"PlayerMat\"\s*,\s*\}\s*,\s*\}\s*,",
        "extra = {\n  },",
        patched,
        count=1,
        flags=re.S,
    )
    patched = re.sub(r"\r?\n  extra = \{\s*.*?\s*  \},\r?\n  perks = \{", "\n  extra = {\n  },\n  perks = {", patched, count=1, flags=re.S)
    patched = re.sub(r"perks\s*=\s*\{.*?\}\s*,\s*\r?\n\s*abilities\s*=", "perks = {\n  },\n  abilities =", patched, count=1, flags=re.S)
    patched = re.sub(r"abilities\s*=\s*\{.*?\n\s*\}\s*\r?\n\}\)", _build_abilities_lua_block(ability_entries) + "\n})", patched, count=1, flags=re.S)
    patched = re.sub(
        r'(tracker\s*=\s*\{\s*image\s*=\s*")([^"]+)(")',
        lambda m: f'{m.group(1)}{class_icon_url}{m.group(3)}',
        patched,
        count=1,
        flags=re.S,
    )
    for alias in profile["template_aliases"]:
        patched = patched.replace(f"{alias}\u00A0 Personal Supply", f"{class_name} Personal Supply")
        patched = patched.replace(f"{alias} Personal Supply", f"{class_name} Personal Supply")
    return patched


def _apply_class_patch(root_data: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    patch_text_value = _make_text_patcher(profile)
    ability_entries = _parse_ability_entries(profile)
    ability_by_card_id = {e["card_id"]: e for e in ability_entries}
    disable_summons = bool(profile.get("disable_summons"))
    disable_summon_card_lua = disable_summons or bool(profile.get("disable_summon_card_lua"))
    summon_card_scripts = {} if disable_summon_card_lua else _extract_source_summon_card_scripts(profile)
    summon_card_aliases = profile.get("summon_card_lua_aliases", {})
    if not isinstance(summon_card_aliases, dict):
        summon_card_aliases = {}
    raw_spawn_only_map = profile.get("summon_card_spawns", {})
    summon_card_spawns: dict[str, list[tuple[str, str]]] = {}
    if isinstance(raw_spawn_only_map, dict):
        for card_name, spec in raw_spawn_only_map.items():
            if not isinstance(card_name, str) or not card_name.strip():
                continue
            entries = _expand_spawn_only_summon_spec(spec)
            if entries:
                summon_card_spawns[_normalize_key(card_name)] = entries
    if disable_summons:
        summon_card_aliases = {}
        summon_card_spawns = {}
    summon_lua_replacements = profile.get("summon_lua_replacements", {})
    if not isinstance(summon_lua_replacements, dict):
        summon_lua_replacements = {}
    summon_card_template_lua = next(
        (
            lua
            for lua in summon_card_scripts.values()
            if isinstance(lua, str) and "SummonCard.forSummon(" in lua and 'require("Component.SummonCard")' in lua
        ),
        None,
    )

    def _apply_summon_lua_replacements(lua_text: str) -> str:
        patched_lua = lua_text
        for src, dst in summon_lua_replacements.items():
            if isinstance(src, str) and src and isinstance(dst, str):
                patched_lua = patched_lua.replace(src, dst)
        return patched_lua

    def _apply_summon_card_script(obj: dict[str, Any], card_name: str) -> None:
        spawn_entries = summon_card_spawns.get(_normalize_key(card_name))
        lookup = summon_card_aliases.get(card_name, card_name)
        summon_lua = summon_card_scripts.get(_normalize_key(lookup))
        lua_to_apply = None
        if isinstance(summon_lua, str) and summon_lua.strip():
            lua_to_apply = _apply_summon_lua_replacements(summon_lua)
        elif spawn_entries and isinstance(summon_card_template_lua, str) and summon_card_template_lua.strip():
            lua_to_apply = _apply_summon_lua_replacements(summon_card_template_lua)

        if isinstance(lua_to_apply, str) and lua_to_apply.strip():
            if spawn_entries and "SummonCard.forSummon(" in lua_to_apply:
                lua_to_apply = _patch_summon_card_lua_spawn_only(lua_to_apply, spawn_entries)
            obj["LuaScript"] = lua_to_apply
            obj["LuaScriptState"] = ""
        elif isinstance(obj.get("LuaScript"), str) and "SummonCard.forSummon(" in obj["LuaScript"]:
            obj["LuaScript"] = ""
            obj["LuaScriptState"] = ""

    starting_ids, advanced_ids = _compute_ability_deck_ids(ability_entries)
    attack_modifier_ids = profile.get("attack_modifier_deck_ids")

    def patch_custom_deck(custom_deck: dict[str, Any]) -> None:
        for deck_key, deck_info in custom_deck.items():
            if not isinstance(deck_info, dict):
                continue
            if deck_key == "3453" and profile["ability_face_url"] and profile["ability_back_url"]:
                deck_info["FaceURL"] = profile["ability_face_url"]
                deck_info["BackURL"] = profile["ability_back_url"]
                deck_info["NumWidth"] = int(profile.get("ability_num_width", 8))
                deck_info["NumHeight"] = int(profile.get("ability_num_height", 4))
            elif deck_key == "5019" and profile.get("amd_face_url") and profile.get("amd_back_url"):
                deck_info["FaceURL"] = profile["amd_face_url"]
                deck_info["BackURL"] = profile["amd_back_url"]
                deck_info["NumWidth"] = 5
                deck_info["NumHeight"] = 5
            elif deck_key == "5021" and profile.get("extra_face_url") and profile.get("extra_back_url"):
                deck_info["FaceURL"] = profile["extra_face_url"]
                deck_info["BackURL"] = profile["extra_back_url"]
                deck_info["NumWidth"] = 2
                deck_info["NumHeight"] = 2

    def patch_object(obj: dict[str, Any]) -> None:
        nickname = obj.get("Nickname")
        if isinstance(obj.get("Description"), str):
            obj["Description"] = patch_text_value(obj["Description"])
        if isinstance(obj.get("Memo"), str):
            memo = obj["Memo"]
            try:
                memo_obj = json.loads(memo)
            except json.JSONDecodeError:
                memo_obj = None
            if isinstance(memo_obj, dict) and isinstance(memo_obj.get("name"), str):
                memo_obj["name"] = patch_text_value(memo_obj["name"])
                obj["Memo"] = json.dumps(memo_obj, ensure_ascii=False, separators=(",", ":"))
        if isinstance(nickname, str):
            obj["Nickname"] = patch_text_value(nickname)
            nickname = obj["Nickname"]

        if isinstance(obj.get("Name"), str):
            obj["Name"] = patch_text_value(obj["Name"])

        if isinstance(obj.get("XmlUI"), str):
            xml = _normalize_spaces(obj["XmlUI"])
            for alias in profile["template_aliases"]:
                xml = xml.replace(alias + " _Icon", profile["class_icon_name"])
                xml = xml.replace(alias + "_Icon", profile["class_icon_name"])
                xml = xml.replace(alias + "\u00A0_Icon", profile["class_icon_name"])
            obj["XmlUI"] = xml

        custom_ui_assets = obj.get("CustomUIAssets")
        if isinstance(custom_ui_assets, list):
            for asset in custom_ui_assets:
                if not isinstance(asset, dict):
                    continue
                name = asset.get("Name")
                if isinstance(name, str):
                    lower = _normalize_key(name)
                    if "icon" in lower and any(_normalize_key(a) in lower for a in profile["template_aliases"]):
                        asset["Name"] = profile["class_icon_name"]
                        name = profile["class_icon_name"]
                if name == profile["class_icon_name"]:
                    asset["URL"] = profile["class_icon_url"]

        if isinstance(obj.get("CustomDeck"), dict):
            patch_custom_deck(obj["CustomDeck"])

        if isinstance(obj.get("LuaScript"), str):
            lua = obj["LuaScript"]
            if _contains_class_lua(lua):
                obj["LuaScript"] = _patch_outer_class_lua(lua, profile, ability_entries)

        card_id = obj.get("CardID")
        if isinstance(card_id, int):
            meta = ability_by_card_id.get(card_id)
            if meta is not None:
                obj["Nickname"] = f'{meta["name"]} ({meta["initiative"]})'
                _apply_summon_card_script(obj, meta["name"])

        if nickname == "Attack Modifiers" and isinstance(obj.get("DeckIDs"), list) and isinstance(attack_modifier_ids, list):
            obj["DeckIDs"] = attack_modifier_ids.copy()
            obj["ColorDiffuse"] = WHITE_DIFFUSE.copy()
            contained = obj.get("ContainedObjects")
            if isinstance(contained, list):
                keep_ids = set(attack_modifier_ids)
                filtered_cards: list[dict[str, Any]] = []
                for card in contained:
                    if not isinstance(card, dict) or card.get("CardID") not in keep_ids:
                        continue
                    card["ColorDiffuse"] = WHITE_DIFFUSE.copy()
                    filtered_cards.append(card)
                obj["ContainedObjects"] = filtered_cards

        if nickname == "Starting Abilities" and isinstance(obj.get("DeckIDs"), list):
            if obj.get("Name") == "Deck":
                obj["Name"] = "DeckCustom"
            obj["DeckIDs"] = starting_ids.copy()

        if nickname == "Advanced Abilities" and isinstance(obj.get("DeckIDs"), list):
            if obj.get("Name") == "Deck":
                obj["Name"] = "DeckCustom"
            obj["DeckIDs"] = advanced_ids.copy()

        if nickname == "Attack Modifiers" and obj.get("Name") == "Deck":
            obj["Name"] = "DeckCustom"

        if nickname == "Character Sheet" and isinstance(obj.get("CustomImage"), dict):
            custom_image = obj["CustomImage"]
            if profile["sheet_front_url"]:
                custom_image["ImageURL"] = profile["sheet_front_url"]
            if profile["sheet_back_url"]:
                custom_image["ImageSecondaryURL"] = profile["sheet_back_url"]

        if nickname == "Character Mat" and isinstance(obj.get("CustomImage"), dict) and profile["character_mat_url"]:
            custom_image = obj["CustomImage"]
            custom_image["ImageURL"] = profile["character_mat_url"]
            custom_image["ImageSecondaryURL"] = profile["character_mat_url"]

        if nickname == "Character Sheet" and isinstance(obj.get("LuaScript"), str):
            obj["LuaScript"] = _patch_character_sheet_lua(obj["LuaScript"], profile)

        if nickname == profile["class_name"] and obj.get("Name") == "Custom_Model_Bag" and isinstance(obj.get("CustomMesh"), dict):
            custom_mesh = obj["CustomMesh"]
            custom_mesh["MeshURL"] = profile["class_box_mesh_url"]
            custom_mesh["DiffuseURL"] = profile["class_box_diffuse_url"]
            custom_mesh["MaterialIndex"] = 3
            custom_mesh["TypeIndex"] = 6

            ui_assets = obj.get("CustomUIAssets")
            if isinstance(ui_assets, list):
                by_name = {a.get("Name"): a for a in ui_assets if isinstance(a, dict) and isinstance(a.get("Name"), str)}
                front = by_name.get("character-box-mask-front")
                side = by_name.get("character-box-mask-side")
                icon = by_name.get(profile["class_icon_name"])
                if front is None:
                    front = {"Type": 0, "Name": "character-box-mask-front", "URL": profile["box_mask_front_url"]}
                    ui_assets.append(front)
                if side is None:
                    side = {"Type": 0, "Name": "character-box-mask-side", "URL": profile["box_mask_side_url"]}
                    ui_assets.append(side)
                if icon is None:
                    icon = {"Type": 0, "Name": profile["class_icon_name"], "URL": profile["class_icon_url"]}
                    ui_assets.append(icon)
                front["URL"] = profile["box_mask_front_url"]
                side["URL"] = profile["box_mask_side_url"]
                icon["URL"] = profile["class_icon_url"]
                icon["Name"] = profile["class_icon_name"]

        if nickname == f"{profile['class_name']} Content Box" and obj.get("Name") == "Custom_Model_Bag" and isinstance(obj.get("CustomMesh"), dict):
            custom_mesh = obj["CustomMesh"]
            custom_mesh["MeshURL"] = profile["content_box_mesh_url"]
            custom_mesh["DiffuseURL"] = profile["content_box_diffuse_url"]
            custom_mesh["MaterialIndex"] = 1
            custom_mesh["TypeIndex"] = 6
            ui_assets = obj.get("CustomUIAssets")
            if isinstance(ui_assets, list):
                content_icon = None
                for asset in ui_assets:
                    if isinstance(asset, dict) and asset.get("Name") == "Gloomhaven 2E_ContentIcon":
                        content_icon = asset
                        break
                if content_icon is None:
                    content_icon = {"Type": 0, "Name": "Gloomhaven 2E_ContentIcon", "URL": profile["content_box_icon_url"]}
                    ui_assets.append(content_icon)
                content_icon["URL"] = profile["content_box_icon_url"]

        if (
            obj.get("GUID") in {profile["legacy_class_bag_guid"], profile["class_bag_guid"]}
            and obj.get("Name") == "Custom_Model_Infinite_Bag"
            and isinstance(obj.get("CustomMesh"), dict)
        ):
            obj["GUID"] = profile["class_bag_guid"]
            custom_mesh = obj["CustomMesh"]
            custom_mesh["MeshURL"] = profile["class_top_box_mesh_url"]
            custom_mesh["DiffuseURL"] = profile["class_top_box_diffuse_url"]
            custom_mesh["MaterialIndex"] = 3
            custom_mesh["TypeIndex"] = 7
            ui_assets = obj.get("CustomUIAssets")
            if isinstance(ui_assets, list):
                found = False
                for asset in ui_assets:
                    if not isinstance(asset, dict):
                        continue
                    name = asset.get("Name")
                    if isinstance(name, str) and (
                        name == profile["class_icon_name"]
                        or ("icon" in _normalize_key(name) and any(_normalize_key(a) in _normalize_key(name) for a in profile["template_aliases"]))
                    ):
                        asset["Name"] = profile["class_icon_name"]
                        asset["URL"] = profile["class_top_box_icon_url"]
                        found = True
                        break
                if not found:
                    ui_assets.append({"Type": 0, "Name": profile["class_icon_name"], "URL": profile["class_top_box_icon_url"]})

        tags = obj.get("Tags")
        if (
            nickname == profile["class_name"]
            and obj.get("Description") is not None
            and isinstance(tags, list)
            and "Character" in tags
            and "Figure" in tags
        ):
            current_guid = obj.get("GUID")
            current_nickname = obj.get("Nickname")
            current_transform = obj.get("Transform")
            current_color = obj.get("ColorDiffuse")

            template = copy.deepcopy(_load_scoundrel_figure_template())
            obj.clear()
            obj.update(template)

            if current_guid is not None:
                obj["GUID"] = current_guid
            if current_nickname is not None:
                obj["Nickname"] = current_nickname
            if current_transform is not None:
                obj["Transform"] = current_transform
            if isinstance(current_color, dict):
                obj["ColorDiffuse"] = current_color

            obj["Description"] = ""
            obj["Tags"] = ["Character", "Figure"]
            obj["LuaScriptState"] = ""
            if isinstance(obj.get("LuaScript"), str):
                obj["LuaScript"] = _patch_figure_lua_starting_health(obj["LuaScript"], int(profile["hp"][0]))

            if profile.get("figure_assetbundle_url"):
                obj["Name"] = "Custom_Assetbundle"
                obj["CustomAssetbundle"] = {
                    "AssetbundleURL": profile["figure_assetbundle_url"],
                    "AssetbundleSecondaryURL": "",
                    "MaterialIndex": 3,
                    "TypeIndex": 1,
                    "LoopingEffectIndex": 0,
                }
                obj.pop("CustomMesh", None)
            elif profile.get("figure_mesh_url"):
                obj["Name"] = "Custom_Model"
                obj["CustomMesh"] = {
                    "MeshURL": profile["figure_mesh_url"],
                    "DiffuseURL": profile.get("figure_diffuse_url") or "",
                    "NormalURL": profile.get("figure_normal_url") or "",
                    "ColliderURL": "",
                    "Convex": 0,
                    "MaterialIndex": 3,
                    "TypeIndex": 0,
                    "CastShadows": 1,
                }
                obj.pop("CustomAssetbundle", None)

        for key in ("GUID", "Description", "Memo", "LuaScript", "LuaScriptState", "XmlUI"):
            value = obj.get(key)
            if isinstance(value, str) and profile["legacy_id_prefix"] in value:
                obj[key] = value.replace(profile["legacy_id_prefix"], profile["class_id_prefix"])

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            patch_object(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    def prune(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                prune(value)
        elif isinstance(node, list):
            filtered = []
            for item in node:
                if isinstance(item, dict):
                    nick = item.get("Nickname")
                    if isinstance(nick, str):
                        normalized = _normalize_key(nick)
                        if normalized in DROP_OBJECT_NICKNAMES:
                            continue
                        if "personal supply" in normalized or "decorative crate" in normalized:
                            continue
                prune(item)
                filtered.append(item)
            node[:] = filtered

    def rebalance_ability_contained_objects(root: Any) -> None:
        starting = _find_first_by_nickname(root, "Starting Abilities")
        advanced = _find_first_by_nickname(root, "Advanced Abilities")
        if not isinstance(starting, dict) or not isinstance(advanced, dict):
            return
        start_cards = starting.get("ContainedObjects")
        adv_cards = advanced.get("ContainedObjects")
        if not isinstance(start_cards, list) or not isinstance(adv_cards, list):
            return

        card_by_id: dict[int, dict[str, Any]] = {}
        for card in [*start_cards, *adv_cards]:
            if isinstance(card, dict) and isinstance(card.get("CardID"), int):
                card_by_id[card["CardID"]] = card

        template = next((card for card in [*start_cards, *adv_cards] if isinstance(card, dict)), None)
        if template is None:
            return

        def build_list(deck_ids: list[int]) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for cid in deck_ids:
                card = card_by_id.get(cid)
                if card is not None:
                    meta = ability_by_card_id.get(cid)
                    if meta is not None:
                        card["Nickname"] = f'{meta["name"]} ({meta["initiative"]})'
                        _apply_summon_card_script(card, meta["name"])
                    out.append(card)
                    continue
                clone = dict(template)
                clone["CardID"] = cid
                meta = ability_by_card_id.get(cid)
                if meta is not None:
                    clone["Nickname"] = f'{meta["name"]} ({meta["initiative"]})'
                    _apply_summon_card_script(clone, meta["name"])
                else:
                    clone["Nickname"] = f"Ability Card {cid}"
                out.append(clone)
            return out

        starting["ContainedObjects"] = build_list(starting_ids)
        advanced["ContainedObjects"] = build_list(advanced_ids)

    data = copy.deepcopy(root_data)
    _ensure_source_class_children(data, profile)
    _replace_attack_modifiers_from_source(data, profile)
    walk(data)
    prune(data)
    if disable_summons:
        _remove_class_summons(data, profile)
        _clear_outer_class_summon_registration(data, profile)
    else:
        _ensure_class_summons(data, profile)
        _ensure_outer_class_summon_registration(data, profile)
    rebalance_ability_contained_objects(data)
    if isinstance(data, dict) and "SaveName" in data:
        data["SaveName"] = f"{profile['class_name']} Test Save (v2)"
    return data


def _extract_root_object(data: dict[str, Any]) -> dict[str, Any]:
    if isinstance(data.get("ObjectStates"), list) and data["ObjectStates"]:
        root = data["ObjectStates"][0]
        if isinstance(root, dict):
            return root
    return data


def _extract_class_outer_object(root: dict[str, Any], class_name: str) -> dict[str, Any]:
    assets_bag = build_skeleton.find_assets_bag(root)
    classes_bag = build_skeleton.find_classes_bag(assets_bag)
    for obj in classes_bag.get("ContainedObjects", []) or []:
        if not isinstance(obj, dict):
            continue
        if obj.get("Name") == "Custom_Model_Infinite_Bag" and _normalize_key(obj.get("Nickname", "")) == _normalize_key(class_name):
            return obj
    raise RuntimeError(f"Could not find class outer object for {class_name}")


def _build_single(global_cfg: dict[str, Any], profile: dict[str, Any], out_saved: Path, out_object_state: Path) -> None:
    base = _build_single_base_object(global_cfg, profile)
    patched = _apply_class_patch(base, profile)
    root = _extract_root_object(patched)
    deduped = _dedupe_guids(root)
    if deduped:
        print(f"Deduped {deduped} duplicate GUID(s) in {profile['class_id']} output.")

    wrapped = patched if "ObjectStates" in patched else build_skeleton.wrap_as_save(root, profile["class_name"])
    if isinstance(wrapped, dict):
        wrapped["SaveName"] = f"{profile['class_name']} Test Save (v2)"
    _save_json(out_saved, wrapped)
    _save_json(out_object_state, root)

    guid_counts = _collect_guid_counts(root)
    dups = [g for g, c in guid_counts.items() if c > 1]
    if dups:
        print(f"Warning: {len(dups)} duplicate GUIDs detected in single-class output for {profile['class_id']}.")


def _build_pack(global_cfg: dict[str, Any], classes_cfg: dict[str, Any], class_ids: list[str], out_saved: Path, singles_dir: Path) -> None:
    if not class_ids:
        raise RuntimeError("No class IDs provided for pack build.")

    class_roots: list[dict[str, Any]] = []
    class_objects: list[dict[str, Any]] = []
    class_names: list[str] = []

    for class_id in class_ids:
        if class_id not in classes_cfg:
            raise RuntimeError(f"Unknown class id: {class_id}")
        raw_profile = classes_cfg[class_id]
        profile = _resolve_profile(global_cfg, raw_profile)
        class_names.append(profile["class_name"])
        single_saved_path = singles_dir / f"{profile['output_prefix']}_saved_object_v2_testable.json"
        if not single_saved_path.exists():
            raise RuntimeError(f"Missing single-class saved object: {single_saved_path}")
        data = _load_json(single_saved_path)
        root = _extract_root_object(data)
        class_roots.append(root)
        class_objects.append(copy.deepcopy(_extract_class_outer_object(root, profile["class_name"])))

    pack_root = copy.deepcopy(class_roots[0])
    assets_bag = build_skeleton.find_assets_bag(pack_root)
    classes_bag = build_skeleton.find_classes_bag(assets_bag)
    classes_bag["ContainedObjects"] = class_objects
    pack_root["Nickname"] = "GH2E Classes Content Box"
    pack_root["Description"] = f"Custom GH2E class pack: {', '.join(class_names)}"

    wrapped = build_skeleton.wrap_as_save(pack_root, "GH2E Classes Pack")
    wrapped["SaveName"] = f"GH2E Multi-Class Pack ({len(class_ids)} classes)"
    _save_json(out_saved, wrapped)

    guid_counts = _collect_guid_counts(pack_root)
    dups = [g for g, c in guid_counts.items() if c > 1]
    if dups:
        print(f"Warning: {len(dups)} duplicate GUIDs detected in pack output.")
    else:
        print("No duplicate GUIDs detected in pack output.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", default="data/class_profiles.json", help="Class profile config JSON.")

    subparsers = parser.add_subparsers(dest="cmd", required=True)

    single = subparsers.add_parser("single", help="Build one class test object.")
    single.add_argument("--class-id", required=True, help="Class profile id (e.g. silent_knife, bruiser).")
    single.add_argument("--out-saved", default=None, help="Saved object output path.")
    single.add_argument("--out-object-state", default=None, help="Object state output path.")

    pack = subparsers.add_parser("pack", help="Build multi-class content pack from built single-class objects.")
    pack.add_argument("--class-ids", required=True, help="Comma-separated class ids.")
    pack.add_argument("--singles-dir", default="dist", help="Directory containing <OutputPrefix>_saved_object_v2_testable.json files.")
    pack.add_argument("--out-saved", default="dist/GH2E_multi_class_content_pack_saved_object_v1.json", help="Output path for pack saved object.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    global_cfg, classes_cfg = _load_profiles(Path(args.profiles))

    if args.cmd == "single":
        class_id = args.class_id
        if class_id not in classes_cfg:
            raise RuntimeError(f"Unknown class id: {class_id}")
        profile = _resolve_profile(global_cfg, classes_cfg[class_id])
        out_saved = Path(args.out_saved) if args.out_saved else Path("dist") / f"{profile['output_prefix']}_saved_object_v2_testable.json"
        out_object = (
            Path(args.out_object_state)
            if args.out_object_state
            else Path("dist") / f"{profile['output_prefix']}_object_state_v2_testable.json"
        )
        _build_single(global_cfg, profile, out_saved, out_object)
        print(f"Wrote: {out_saved}")
        print(f"Wrote: {out_object}")
        return 0

    if args.cmd == "pack":
        class_ids = [c.strip() for c in args.class_ids.split(",") if c.strip()]
        _build_pack(global_cfg, classes_cfg, class_ids, Path(args.out_saved), Path(args.singles_dir))
        print(f"Wrote: {args.out_saved}")
        return 0

    raise RuntimeError(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
