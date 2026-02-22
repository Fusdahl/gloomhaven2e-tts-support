#!/usr/bin/env python3
"""Build a new, testable Silent Knife saved object without mutating existing outputs.

This script rewrites asset URLs and selected deck metadata in a copied JSON file.
It supports both full-save JSON (with ObjectStates) and single object-state JSON.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


RAW_BASE = "https://raw.githubusercontent.com/Fusdahl/gloomhaven2e-tts-support/main/assets/"
CLASS_NAME = "Silent Knife"
CLASS_ICON_NAME = "Silent_Knife_Icon"
SILENT_KNIFE_HP = [8, 9, 11, 12, 14, 15, 17, 18, 20]
ASSET_REV = "r20260222a"
SILENT_KNIFE_ORDER_FILE = (
    Path(__file__).resolve().parent.parent
    / "assets"
    / "silent_knife_asset_downloads"
    / "ordered_for_rows"
    / "ORDER.txt"
)

ABILITY_FACE = RAW_BASE + "final_class_ability_atlases/silent_knife_ability_atlas.png" + f"?v={ASSET_REV}"
ABILITY_BACK = RAW_BASE + "final_class_ability_atlases/silent_knife_ability_back.png" + f"?v={ASSET_REV}"

# Quartermaster-compatible layout (5x5) with filler + back in slot 24.
AMD_FACE = RAW_BASE + "final_class_amd_atlases/silent_knife_amd_atlas_5x5.png" + f"?v={ASSET_REV}"
AMD_BACK = RAW_BASE + "final_class_amd_atlases/silent_knife_amd_back_814x531.png" + f"?v={ASSET_REV}"

EXTRA_FACE = RAW_BASE + "final_class_amd_atlases/silent_knife_extra_perks_atlas_2x2.png" + f"?v={ASSET_REV}"
EXTRA_BACK = AMD_BACK

SHEET_FRONT = RAW_BASE + "FH_compatible_sheets/silent_knife_character_sheet_front.png" + f"?v={ASSET_REV}"
SHEET_BACK = RAW_BASE + "FH_compatible_sheets/silent_knife_character_sheet_back.png" + f"?v={ASSET_REV}"

# Keep extra cards but prevent 5019 filler slots from becoming drawable.
SAFE_ATTACK_MODIFIER_DECK_IDS = [
    501911,
    501910,
    501909,
    501908,
    501907,
    501906,
    501905,
    501904,
    501903,
    501902,
    501901,
    501900,
    502102,
    502101,
    502100,
]

# Ability slot mapping for the Silent Knife 8x4 atlas.
# Atlas ordering is row-major with cards in slots 00..27.
# - L1 + X cards occupy 00..11 (12 cards) => Starting Abilities
# - L2+ cards occupy 12..27 (16 cards) => Advanced Abilities
STARTING_ABILITY_DECK_IDS = [345311, 345310, 345309, 345308, 345307, 345306, 345305, 345304, 345303, 345302, 345301, 345300]
ADVANCED_ABILITY_DECK_IDS = [345327, 345326, 345325, 345324, 345323, 345322, 345321, 345320, 345319, 345318, 345317, 345316, 345315, 345314, 345313, 345312]

# Silent Knife sheet-aligned checkmark positions (best-fit from image comparison).
SILENT_KNIFE_PERK_POSITIONS = [
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
    (80, -348),
    (80, -388),
]

SILENT_KNIFE_MASTERY_POSITIONS = [
    (-336, -339),
    (-336, -430),
]

WHITE_DIFFUSE = {"r": 1.0, "g": 1.0, "b": 1.0}
DROP_OBJECT_NICKNAMES = {
    "character mat",
    "decorative crate",
    "quartermaster personal supply",
    "silent knife personal supply",
}

_ABILITY_ENTRIES_CACHE: list[dict[str, Any]] | None = None
_ABILITY_BY_CARD_ID_CACHE: dict[int, dict[str, Any]] | None = None


def _normalize_spaces(text: str) -> str:
    return text.replace("\u00A0", " ")


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", _normalize_spaces(text)).strip().lower()


def _slug_to_display_name(slug: str) -> str:
    special = {
        "tricksters": "Trickster's",
        "duelists": "Duelist's",
    }
    parts = slug.split("-")
    out_parts: list[str] = []
    for part in parts:
        if part in special:
            out_parts.append(special[part])
        else:
            out_parts.append(part.capitalize())
    return " ".join(out_parts)


def _load_silent_knife_ability_entries() -> list[dict[str, Any]]:
    global _ABILITY_ENTRIES_CACHE
    if _ABILITY_ENTRIES_CACHE is not None:
        return _ABILITY_ENTRIES_CACHE

    if not SILENT_KNIFE_ORDER_FILE.exists():
        raise RuntimeError(f"Missing Silent Knife order file: {SILENT_KNIFE_ORDER_FILE}")

    entries: list[dict[str, Any]] = []
    lines = SILENT_KNIFE_ORDER_FILE.read_text(encoding="utf-8").splitlines()
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
        card_name = _slug_to_display_name(slug)
        entries.append(
            {
                "idx": idx,
                "card_id": 345299 + idx,
                "name": card_name,
                "level": level,
                "initiative": initiative,
            }
        )

    entries.sort(key=lambda x: x["idx"])
    if len(entries) != 28:
        raise RuntimeError(
            f"Expected 28 Silent Knife ability entries, got {len(entries)} from {SILENT_KNIFE_ORDER_FILE}"
        )
    _ABILITY_ENTRIES_CACHE = entries
    return entries


def _get_ability_by_card_id() -> dict[int, dict[str, Any]]:
    global _ABILITY_BY_CARD_ID_CACHE
    if _ABILITY_BY_CARD_ID_CACHE is not None:
        return _ABILITY_BY_CARD_ID_CACHE
    entries = _load_silent_knife_ability_entries()
    _ABILITY_BY_CARD_ID_CACHE = {entry["card_id"]: entry for entry in entries}
    return _ABILITY_BY_CARD_ID_CACHE


def _build_abilities_lua_block() -> str:
    lines = ["  abilities = {"]
    for entry in _load_silent_knife_ability_entries():
        level = entry["level"]
        if level.upper() == "X":
            level_lua = '"X"'
        else:
            level_lua = str(int(level))
        lines.append(f'    ["{entry["name"]}"] = {{')
        lines.append(f"      level = {level_lua},")
        lines.append(f'      initiative = {entry["initiative"]},')
        lines.append("    },")
    lines.append("  }")
    return "\n".join(lines)


def _contains_class_lua(lua_script: str) -> bool:
    return (
        "ClassApi.registerClass(" in lua_script
        and "perks" in lua_script
        and "abilities" in lua_script
    )


def _patch_outer_class_lua(lua_script: str) -> str:
    patched = re.sub(
        r'ClassApi\.registerClass\("([^"]+)"',
        f'ClassApi.registerClass("{CLASS_NAME}"',
        lua_script,
        count=1,
    )
    hp_values = "".join(f"    {value},\n" for value in SILENT_KNIFE_HP)
    hp_block = "hp = {\n" + hp_values + "  },"
    patched = re.sub(
        r"hp\s*=\s*\{\s*[\d,\s]*\s*\},",
        hp_block,
        patched,
        count=1,
        flags=re.S,
    )
    # Remove template-only extras so no missing-object spawn is attempted.
    patched = re.sub(
        r"extra\s*=\s*\{\s*\{\s*name\s*=\s*\"Decorative crate\"\s*,\s*target\s*=\s*\"PlayerMat\"\s*,\s*\}\s*,\s*\{\s*name\s*=\s*\"[^\"]*Personal Supply\"\s*,\s*target\s*=\s*\"PlayerMat\"\s*,\s*\}\s*,\s*\}\s*,",
        "extra = {\n  },",
        patched,
        count=1,
        flags=re.S,
    )
    patched = re.sub(
        r"\r?\n  extra = \{\s*.*?\s*  \},\r?\n  perks = \{",
        "\n  extra = {\n  },\n  perks = {",
        patched,
        count=1,
        flags=re.S,
    )
    # Disable automatic perk transformations; deck can be managed manually.
    patched = re.sub(
        r"perks\s*=\s*\{.*?\}\s*,\s*\r?\n\s*abilities\s*=",
        "perks = {\n  },\n  abilities =",
        patched,
        count=1,
        flags=re.S,
    )
    # Replace ability map with Silent Knife names/levels/initiatives from ORDER.txt.
    ability_block = _build_abilities_lua_block()
    patched = re.sub(
        r"abilities\s*=\s*\{.*?\n\s*\}\s*\r?\n\}\)",
        ability_block + "\n})",
        patched,
        count=1,
        flags=re.S,
    )
    # Keep visible naming coherent for this clone stage.
    patched = patched.replace("Quartermaster\u00A0 Personal Supply", f"{CLASS_NAME} Personal Supply")
    patched = patched.replace("Quartermaster Personal Supply", f"{CLASS_NAME} Personal Supply")
    return patched


def _patch_text_value(text: str) -> str:
    out = _normalize_spaces(text)
    out = out.replace("Quartermaster", CLASS_NAME)
    out = out.replace("Valrath Silent Knife", "Human Silent Knife")
    out = out.replace("Quartermaster clone", "Silent Knife clone")
    out = re.sub(r"\s+", " ", out).strip()
    return out


def _patch_custom_deck(custom_deck: dict[str, Any]) -> None:
    for deck_key, deck_info in custom_deck.items():
        if not isinstance(deck_info, dict):
            continue
        if deck_key == "3453":
            deck_info["FaceURL"] = ABILITY_FACE
            deck_info["BackURL"] = ABILITY_BACK
            deck_info["NumWidth"] = 8
            deck_info["NumHeight"] = 4
        elif deck_key == "5019":
            deck_info["FaceURL"] = AMD_FACE
            deck_info["BackURL"] = AMD_BACK
            deck_info["NumWidth"] = 5
            deck_info["NumHeight"] = 5
        elif deck_key == "5021":
            deck_info["FaceURL"] = EXTRA_FACE
            deck_info["BackURL"] = EXTRA_BACK
            deck_info["NumWidth"] = 2
            deck_info["NumHeight"] = 2


def _patch_character_sheet_lua(lua_script: str) -> str:
    perk_lines = "\n".join(
        f"    {{ {x} , {y} }}," for x, y in SILENT_KNIFE_PERK_POSITIONS
    )
    mastery_lines = "\n".join(
        f"    {{ {x} , {y} }}," for x, y in SILENT_KNIFE_MASTERY_POSITIONS
    )

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

    # Standalone-sheet safety: if owner/player linkage is missing,
    # fall back to click player and avoid hard runtime failures.
    patched = patched.replace(
        "  this.onChangeLevel = function(_, value, element)",
        "  this.onChangeLevel = function(player, value, element)",
        1,
    )
    patched = patched.replace(
        "    CharacterApi.setLevel(this.player, newLevel)",
        """    local targetPlayer = this.player or (player and player.color) or player
    if targetPlayer ~= nil then
      this.player = targetPlayer
      pcall(CharacterApi.setLevel, targetPlayer, newLevel)
    end""",
        1,
    )
    patched = patched.replace(
        "  this.onPerkClicked = function(_, value, element)",
        "  this.onPerkClicked = function(player, value, element)",
        1,
    )
    patched = patched.replace(
        "    CharacterApi.changePerk(this.player, perk, value)",
        """    local targetPlayer = this.player or (player and player.color) or player
    if targetPlayer ~= nil then
      this.player = targetPlayer
      pcall(CharacterApi.changePerk, targetPlayer, perk, value)
    end""",
        1,
    )
    return patched


def _patch_object(obj: dict[str, Any]) -> None:
    nickname = obj.get("Nickname")

    if isinstance(obj.get("Description"), str):
        obj["Description"] = _patch_text_value(obj["Description"])
    if isinstance(obj.get("Memo"), str):
        memo = obj["Memo"]
        try:
            memo_obj = json.loads(memo)
        except json.JSONDecodeError:
            memo_obj = None
        if isinstance(memo_obj, dict):
            changed = False
            if isinstance(memo_obj.get("name"), str):
                memo_obj["name"] = _patch_text_value(memo_obj["name"])
                changed = True
            if changed:
                obj["Memo"] = json.dumps(memo_obj, ensure_ascii=False, separators=(",", ":"))

    if isinstance(nickname, str):
        obj["Nickname"] = _patch_text_value(nickname)
        nickname = obj["Nickname"]

    if isinstance(obj.get("Name"), str) and "Quartermaster" in _normalize_spaces(obj["Name"]):
        obj["Name"] = _patch_text_value(obj["Name"])

    if isinstance(obj.get("XmlUI"), str):
        xml = _normalize_spaces(obj["XmlUI"])
        xml = xml.replace("Quartermaster _Icon", CLASS_ICON_NAME)
        xml = xml.replace("Quartermaster_Icon", CLASS_ICON_NAME)
        xml = xml.replace("Quartermaster\u00A0_Icon", CLASS_ICON_NAME)
        obj["XmlUI"] = xml

    custom_ui_assets = obj.get("CustomUIAssets")
    if isinstance(custom_ui_assets, list):
        for asset in custom_ui_assets:
            if not isinstance(asset, dict):
                continue
            name = asset.get("Name")
            if isinstance(name, str) and "Quartermaster" in _normalize_spaces(name):
                asset["Name"] = CLASS_ICON_NAME

    if isinstance(obj.get("CustomDeck"), dict):
        _patch_custom_deck(obj["CustomDeck"])

    if isinstance(obj.get("LuaScript"), str):
        lua = obj["LuaScript"]
        if _contains_class_lua(lua):
            obj["LuaScript"] = _patch_outer_class_lua(lua)

    card_id = obj.get("CardID")
    if isinstance(card_id, int):
        ability_map = _get_ability_by_card_id()
        meta = ability_map.get(card_id)
        if meta is not None:
            obj["Nickname"] = f'{meta["name"]} ({meta["initiative"]})'

    if nickname == "Attack Modifiers" and isinstance(obj.get("DeckIDs"), list):
        obj["DeckIDs"] = SAFE_ATTACK_MODIFIER_DECK_IDS.copy()
        obj["ColorDiffuse"] = WHITE_DIFFUSE.copy()
        # Keep contained cards consistent with DeckIDs to avoid deck mismatch issues.
        contained = obj.get("ContainedObjects")
        if isinstance(contained, list):
            keep_ids = set(SAFE_ATTACK_MODIFIER_DECK_IDS)
            filtered_cards: list[dict[str, Any]] = []
            for card in contained:
                if not isinstance(card, dict) or card.get("CardID") not in keep_ids:
                    continue
                card["ColorDiffuse"] = WHITE_DIFFUSE.copy()
                filtered_cards.append(card)
            obj["ContainedObjects"] = filtered_cards

    if nickname == "Starting Abilities" and isinstance(obj.get("DeckIDs"), list):
        obj["DeckIDs"] = STARTING_ABILITY_DECK_IDS.copy()

    if nickname == "Advanced Abilities" and isinstance(obj.get("DeckIDs"), list):
        obj["DeckIDs"] = ADVANCED_ABILITY_DECK_IDS.copy()

    if nickname in {"Character Sheet", "Character Mat"} and isinstance(obj.get("CustomImage"), dict):
        custom_image = obj["CustomImage"]
        custom_image["ImageURL"] = SHEET_FRONT
        custom_image["ImageSecondaryURL"] = SHEET_BACK

    if nickname == "Character Sheet" and isinstance(obj.get("LuaScript"), str):
        obj["LuaScript"] = _patch_character_sheet_lua(obj["LuaScript"])


def _walk_and_patch(node: Any) -> None:
    if isinstance(node, dict):
        _patch_object(node)
        for value in node.values():
            _walk_and_patch(value)
    elif isinstance(node, list):
        for item in node:
            _walk_and_patch(item)


def _prune_character_mat(node: Any) -> None:
    if isinstance(node, dict):
        for value in node.values():
            _prune_character_mat(value)
    elif isinstance(node, list):
        filtered = []
        for item in node:
            if isinstance(item, dict):
                nick = item.get("Nickname")
                if isinstance(nick, str):
                    normalized = _normalize_key(nick)
                    if normalized in DROP_OBJECT_NICKNAMES:
                        continue
                    if "personal supply" in normalized:
                        continue
                    if "decorative crate" in normalized:
                        continue
            _prune_character_mat(item)
            filtered.append(item)
        node[:] = filtered


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


def _rebalance_ability_contained_objects(root: Any) -> None:
    starting = _find_first_by_nickname(root, "Starting Abilities")
    advanced = _find_first_by_nickname(root, "Advanced Abilities")
    if not isinstance(starting, dict) or not isinstance(advanced, dict):
        return

    start_cards = starting.get("ContainedObjects")
    adv_cards = advanced.get("ContainedObjects")
    if not isinstance(start_cards, list) or not isinstance(adv_cards, list):
        return

    # Build a lookup of all existing ability card objects across both decks.
    card_by_id: dict[int, dict[str, Any]] = {}
    for card in [*start_cards, *adv_cards]:
        if isinstance(card, dict) and isinstance(card.get("CardID"), int):
            card_by_id[card["CardID"]] = card

    # Fallback template if we must synthesize a missing card object.
    template = None
    for card in [*start_cards, *adv_cards]:
        if isinstance(card, dict):
            template = card
            break
    if template is None:
        return

    def build_list(deck_ids: list[int]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for cid in deck_ids:
            card = card_by_id.get(cid)
            if card is not None:
                out.append(card)
                continue
            clone = dict(template)
            clone["CardID"] = cid
            clone["Nickname"] = f"Ability Card {cid}"
            out.append(clone)
        return out

    starting["ContainedObjects"] = build_list(STARTING_ABILITY_DECK_IDS)
    advanced["ContainedObjects"] = build_list(ADVANCED_ABILITY_DECK_IDS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="dist/Silent_Knife_saved_object.json",
        help="Source JSON file to copy+patch.",
    )
    parser.add_argument(
        "--output",
        default="dist/Silent_Knife_saved_object_v2_testable.json",
        help="Destination JSON file.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    data = json.loads(input_path.read_text(encoding="utf-8"))
    _walk_and_patch(data)
    _prune_character_mat(data)
    _rebalance_ability_contained_objects(data)

    # Keep both TTS formats stable:
    # - "saved_object" output => wrapped save JSON with ObjectStates
    # - "object_state" output => raw object-state JSON only
    output_name = output_path.name.lower()
    if "saved_object" in output_name and "ObjectStates" not in data:
        data = {
            "SaveName": f"{CLASS_NAME} Test Save (v2)",
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
            "ObjectStates": [data],
        }
    elif "object_state" in output_name and "ObjectStates" in data:
        object_states = data.get("ObjectStates") or []
        if object_states:
            data = object_states[0]

    # If this is a full save, set a distinct SaveName so it is obvious in TTS load list.
    if isinstance(data, dict) and "SaveName" in data:
        data["SaveName"] = f"{CLASS_NAME} Test Save (v2)"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
