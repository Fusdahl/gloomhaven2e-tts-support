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

ABILITY_FACE = RAW_BASE + "final_class_ability_atlases/silent_knife_ability_atlas.png"
ABILITY_BACK = RAW_BASE + "final_class_ability_atlases/silent_knife_ability_back.png"

# Quartermaster-compatible layout (5x5) with filler + back in slot 24.
AMD_FACE = RAW_BASE + "final_class_amd_atlases/silent_knife_amd_atlas_5x5.png"
AMD_BACK = RAW_BASE + "final_class_amd_atlases/silent_knife_amd_back_814x531.png"

EXTRA_FACE = RAW_BASE + "final_class_amd_atlases/silent_knife_extra_perks_atlas_2x2.png"
EXTRA_BACK = AMD_BACK

SHEET_FRONT = RAW_BASE + "FH_compatible_sheets/silent_knife_character_sheet_front.png"
SHEET_BACK = RAW_BASE + "FH_compatible_sheets/silent_knife_character_sheet_back.png"

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
    (80, -365),
    (80, -441),
]

SILENT_KNIFE_MASTERY_POSITIONS = [
    (-336, -339),
    (-336, -430),
]


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
    return patched


def _patch_object(obj: dict[str, Any]) -> None:
    nickname = obj.get("Nickname")

    if isinstance(obj.get("CustomDeck"), dict):
        _patch_custom_deck(obj["CustomDeck"])

    if nickname == "Attack Modifiers" and isinstance(obj.get("DeckIDs"), list):
        obj["DeckIDs"] = SAFE_ATTACK_MODIFIER_DECK_IDS.copy()
        # Keep contained cards consistent with DeckIDs to avoid deck mismatch issues.
        contained = obj.get("ContainedObjects")
        if isinstance(contained, list):
            keep_ids = set(SAFE_ATTACK_MODIFIER_DECK_IDS)
            obj["ContainedObjects"] = [
                card
                for card in contained
                if isinstance(card, dict) and card.get("CardID") in keep_ids
            ]

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
            if isinstance(item, dict) and item.get("Nickname") == "Character Mat":
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

    # If this is a full save, set a distinct SaveName so it is obvious in TTS load list.
    if isinstance(data, dict) and "SaveName" in data:
        data["SaveName"] = "Silent Knife Test Save (v2)"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
