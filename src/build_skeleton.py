#!/usr/bin/env python3
"""Build a standalone TTS saved object for a single GH2E class.

Current scope:
- Clone the full GH2E content box from the reference mod.
- Keep only one class (Quartermaster template) inside Classes.
- Rename only a few visible labels to the target class name.
- Update the Character Mat image URL(s) to a GitHub raw URL.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import secrets
from pathlib import Path
from typing import Any

RAW_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "Fusdahl/gloomhaven2e-tts-support/main/assets/"
)

QUARTERMASTER_HINTS = ("quartermaster", "three spears")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def normalize(text: str | None) -> str:
    # Normalize common non-breaking spaces from TTS nicknames.
    return (text or "").replace("\u00A0", " ").strip().lower()


def iter_objects(node: Any):
    if isinstance(node, dict):
        if "Name" in node and "GUID" in node:
            yield node
        for value in node.values():
            yield from iter_objects(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_objects(item)


def get_root_content_box(save_data: dict[str, Any]) -> dict[str, Any]:
    object_states = save_data.get("ObjectStates")
    if not isinstance(object_states, list) or not object_states:
        raise RuntimeError("Source mod JSON has no ObjectStates root content box.")
    root = object_states[0]
    if not isinstance(root, dict) or "ContainedObjects" not in root:
        raise RuntimeError("Invalid root content box object in source mod JSON.")
    return root


def find_assets_bag(root_box: dict[str, Any]) -> dict[str, Any]:
    for child in root_box.get("ContainedObjects", []) or []:
        if child.get("GUID") == "assets":
            return child
    for child in root_box.get("ContainedObjects", []) or []:
        if child.get("Name") == "Bag" and normalize(child.get("Nickname")) == "autoassets":
            return child
    raise RuntimeError("Could not find assets bag inside root content box.")


def find_classes_bag(assets_bag: dict[str, Any]) -> dict[str, Any]:
    for child in assets_bag.get("ContainedObjects", []) or []:
        if child.get("GUID") == "classes":
            return child
    for child in assets_bag.get("ContainedObjects", []) or []:
        if child.get("Name") == "Bag" and normalize(child.get("Nickname")) == "classes":
            return child
    raise RuntimeError("Could not find classes bag inside assets bag.")


def find_quartermaster_outer(classes_bag: dict[str, Any]) -> dict[str, Any]:
    for obj in classes_bag.get("ContainedObjects", []) or []:
        if obj.get("Name") != "Custom_Model_Infinite_Bag":
            continue
        for child in obj.get("ContainedObjects", []) or []:
            nick = normalize(child.get("Nickname"))
            if any(hint in nick for hint in QUARTERMASTER_HINTS):
                return obj
    raise RuntimeError("Could not find Quartermaster class in classes bag.")


def find_inner_class_box(outer_bag: dict[str, Any]) -> dict[str, Any]:
    for child in outer_bag.get("ContainedObjects", []) or []:
        if child.get("Name") == "Custom_Model_Bag":
            return child
    raise RuntimeError("Could not find inner class box (Custom_Model_Bag) in cloned class.")


def find_character_mat(inner_box: dict[str, Any]) -> dict[str, Any]:
    for child in inner_box.get("ContainedObjects", []) or []:
        nick = normalize(child.get("Nickname"))
        if child.get("Name") == "Custom_Tile" and "character mat" in nick:
            return child
    raise RuntimeError("Could not find Character Mat object in cloned class.")


def find_character_sheet(inner_box: dict[str, Any]) -> dict[str, Any]:
    for child in inner_box.get("ContainedObjects", []) or []:
        nick = normalize(child.get("Nickname"))
        if child.get("Name") == "Custom_Tile" and "character sheet" in nick:
            return child
    raise RuntimeError("Could not find Character Sheet object in cloned class.")


def find_personal_supply_deck(inner_box: dict[str, Any]) -> dict[str, Any] | None:
    for child in inner_box.get("ContainedObjects", []) or []:
        if child.get("Name") == "Deck" and "personal supply" in normalize(child.get("Nickname")):
            return child
    return None


def find_character_figure(inner_box: dict[str, Any]) -> dict[str, Any] | None:
    for child in inner_box.get("ContainedObjects", []) or []:
        if child.get("Name") == "Custom_Model":
            return child
    return None


def update_outer_class_lua(outer_bag: dict[str, Any], class_name: str) -> None:
    lua = outer_bag.get("LuaScript")
    if not isinstance(lua, str) or not lua:
        raise RuntimeError("Outer class bag is missing LuaScript.")

    # Keep replacements narrow and explicit to avoid changing bundled library internals.
    lua, class_replaced = re.subn(
        r'ClassApi\.registerClass\("([^"]+)"',
        f'ClassApi.registerClass("{class_name}"',
        lua,
        count=1,
    )
    lua, supply_replaced = re.subn(
        r'name = "([^"]*Personal Supply)"',
        f'name = "{class_name} Personal Supply"',
        lua,
        count=1,
    )
    outer_bag["LuaScript"] = lua

    if class_replaced != 1:
        raise RuntimeError("Could not update ClassApi.registerClass(...) in outer LuaScript.")
    if supply_replaced != 1:
        raise RuntimeError("Could not update Personal Supply name in outer LuaScript.")


def random_guid(existing: set[str]) -> str:
    while True:
        guid = "".join(secrets.choice("0123456789abcdef") for _ in range(6))
        if guid not in existing:
            existing.add(guid)
            return guid


def collect_guids(node: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        guid = node.get("GUID")
        if isinstance(guid, str):
            found.add(guid)
        for value in node.values():
            found.update(collect_guids(value))
    elif isinstance(node, list):
        for item in node:
            found.update(collect_guids(item))
    return found


def regenerate_guids(node: Any, seen: set[str]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("GUID"), str):
            node["GUID"] = random_guid(seen)
        for value in node.values():
            regenerate_guids(value, seen)
    elif isinstance(node, list):
        for item in node:
            regenerate_guids(item, seen)


def build_single_object(
    source_mod: dict[str, Any],
    class_data: dict[str, Any],
    image_url: str | None,
    regenerate_class_guids: bool,
    rename_internal_class_identity: bool,
) -> dict[str, Any]:
    class_name = class_data["class_name"]
    root_template = get_root_content_box(source_mod)
    clone = copy.deepcopy(root_template)
    assets_bag = find_assets_bag(clone)
    classes_bag = find_classes_bag(assets_bag)
    quartermaster_outer = find_quartermaster_outer(classes_bag)

    # Keep only one class in the Classes bag.
    classes_bag["ContainedObjects"] = [quartermaster_outer]
    if regenerate_class_guids:
        # Avoid GUID collisions with existing Quartermaster content in the same table.
        used_guids = collect_guids(clone)
        regenerate_guids(quartermaster_outer, seen=used_guids)

    # Minimal visible rename only (leave scripts and component nicknames intact).
    clone["Nickname"] = f"{class_name} Content Box"
    clone["Description"] = f"Single-class content box for {class_name} (Quartermaster clone)"
    quartermaster_outer["Nickname"] = class_name
    if rename_internal_class_identity:
        update_outer_class_lua(quartermaster_outer, class_name)

    inner_box = find_inner_class_box(quartermaster_outer)
    inner_box["Nickname"] = class_name
    if rename_internal_class_identity:
        personal_supply = find_personal_supply_deck(inner_box)
        if personal_supply is not None:
            personal_supply["Nickname"] = f"{class_name} Personal Supply"
        figure = find_character_figure(inner_box)
        if figure is not None:
            figure["Nickname"] = class_name

    character_mat = find_character_mat(inner_box)
    custom_image = character_mat.get("CustomImage")
    if not isinstance(custom_image, dict):
        raise RuntimeError("Character Mat has no CustomImage object.")
    if image_url:
        custom_image["ImageURL"] = image_url
        # Bottom/back image for Custom_Tile; keep in sync to avoid mixed fronts/backs.
        custom_image["ImageSecondaryURL"] = image_url
        character_sheet = find_character_sheet(inner_box)
        sheet_image = character_sheet.get("CustomImage")
        if not isinstance(sheet_image, dict):
            raise RuntimeError("Character Sheet has no CustomImage object.")
        sheet_image["ImageURL"] = image_url
        sheet_image["ImageSecondaryURL"] = image_url

    return clone


def wrap_as_save(single_object: dict[str, Any], class_name: str) -> dict[str, Any]:
    # Minimal SaveState wrapper.
    return {
        "SaveName": f"{class_name} Test Save",
        "Date": "",
        "VersionNumber": "",
        "GameMode": "",
        "GameType": "",
        "GameComplexity": "",
        "Tags": [],
        "Gravity": 0.5,
        "PlayArea": 0.5,
        "Table": "",
        "Sky": "",
        "Note": "",
        "TabStates": {},
        "LuaScript": "",
        "LuaScriptState": "",
        "XmlUI": "",
        "ObjectStates": [single_object],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-mod",
        default="original_mod_json/Gloomhaven 2e classes  mod.json",
        help="Path to source mod JSON used as template.",
    )
    parser.add_argument(
        "--class-data",
        default="data/class_silent_knife.json",
        help="Path to class data JSON file.",
    )
    parser.add_argument(
        "--out-object-state",
        default="dist/Silent_Knife_object_state.json",
        help="Output path for raw ObjectState JSON (debug/advanced use).",
    )
    parser.add_argument(
        "--out-saved-object",
        default="dist/Silent_Knife_saved_object.json",
        help="Output path for wrapped JSON to use in TTS Saved Objects.",
    )
    parser.add_argument(
        "--out-save",
        default="dist/Silent_Knife_save.json",
        help="Output path for a minimal full save JSON.",
    )
    parser.add_argument(
        "--assets-dir",
        default="assets",
        help="Local assets directory used to verify image filenames before URL injection.",
    )
    parser.add_argument(
        "--regenerate-class-guids",
        action="store_true",
        help="Regenerate GUIDs in the cloned class subtree (off by default for safety).",
    )
    parser.add_argument(
        "--rename-internal-class-identity",
        action="store_true",
        help=(
            "Rename internal class identity in Lua (registerClass name, figure/supply names). "
            "Off by default for safety."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_mod_path = Path(args.source_mod)
    class_data_path = Path(args.class_data)
    out_object_state_path = Path(args.out_object_state)
    out_saved_object_path = Path(args.out_saved_object)
    out_save_path = Path(args.out_save)
    assets_dir = Path(args.assets_dir)

    source_mod = load_json(source_mod_path)
    class_data = load_json(class_data_path)
    image_filename = class_data.get("image_filename", "")
    image_url = None
    if image_filename:
        local_image_path = assets_dir / image_filename
        if local_image_path.exists():
            image_url = RAW_BASE_URL + image_filename
        else:
            print(
                f"Warning: {local_image_path} not found; "
                "keeping original Character Mat image URL."
            )

    single_object = build_single_object(
        source_mod,
        class_data,
        image_url,
        regenerate_class_guids=args.regenerate_class_guids,
        rename_internal_class_identity=args.rename_internal_class_identity,
    )
    wrapped = wrap_as_save(single_object, class_data["class_name"])

    save_json(out_object_state_path, single_object)
    save_json(out_saved_object_path, wrapped)
    save_json(out_save_path, wrapped)

    print(f"Wrote raw object state: {out_object_state_path}")
    print(f"Wrote saved object:     {out_saved_object_path}")
    print(f"Wrote full save:        {out_save_path}")


if __name__ == "__main__":
    main()
