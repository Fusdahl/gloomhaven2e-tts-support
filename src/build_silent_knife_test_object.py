#!/usr/bin/env python3
"""Build a new, testable Silent Knife saved object without mutating existing outputs.

This script rewrites asset URLs and selected deck metadata in a copied JSON file.
It supports both full-save JSON (with ObjectStates) and single object-state JSON.
"""

from __future__ import annotations

import argparse
import json
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

    if nickname in {"Character Sheet", "Character Mat"} and isinstance(obj.get("CustomImage"), dict):
        custom_image = obj["CustomImage"]
        custom_image["ImageURL"] = SHEET_FRONT
        custom_image["ImageSecondaryURL"] = SHEET_BACK


def _walk_and_patch(node: Any) -> None:
    if isinstance(node, dict):
        _patch_object(node)
        for value in node.values():
            _walk_and_patch(value)
    elif isinstance(node, list):
        for item in node:
            _walk_and_patch(item)


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
