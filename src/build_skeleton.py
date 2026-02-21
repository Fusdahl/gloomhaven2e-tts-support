#!/usr/bin/env python3
"""Build a standalone TTS saved object for a single GH2E class.

Current scope:
- Clone the Quartermaster class object from the existing reference mod.
- Rename visible fields to Silent Knife (or other class_name from data json).
- Regenerate GUIDs recursively so the clone can coexist with original objects.
- Update the Character Mat image URL to a GitHub raw URL.
"""

from __future__ import annotations

import argparse
import copy
import json
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


def find_quartermaster_outer(save_data: dict[str, Any]) -> dict[str, Any]:
    for obj in iter_objects(save_data.get("ObjectStates", [])):
        if obj.get("Name") != "Custom_Model_Infinite_Bag":
            continue
        for child in obj.get("ContainedObjects", []) or []:
            nick = normalize(child.get("Nickname"))
            if any(hint in nick for hint in QUARTERMASTER_HINTS):
                return obj
    raise RuntimeError("Could not find Quartermaster outer class bag in source mod JSON.")


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


def random_guid(existing: set[str]) -> str:
    while True:
        guid = "".join(secrets.choice("0123456789abcdef") for _ in range(6))
        if guid not in existing:
            existing.add(guid)
            return guid


def regenerate_guids(node: Any, seen: set[str]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("GUID"), str):
            node["GUID"] = random_guid(seen)
        for value in node.values():
            regenerate_guids(value, seen)
    elif isinstance(node, list):
        for item in node:
            regenerate_guids(item, seen)


def rename_visible_fields(node: Any, class_name: str) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("Nickname"), str):
            nick = node["Nickname"]
            node["Nickname"] = (
                nick.replace("Quartermaster", class_name).replace("Three Spears", class_name)
            )
        if isinstance(node.get("Description"), str):
            desc = node["Description"]
            node["Description"] = (
                desc.replace("Quartermaster", class_name).replace("Three Spears", class_name)
            )
        if isinstance(node.get("LuaScript"), str):
            lua = node["LuaScript"]
            node["LuaScript"] = (
                lua.replace("Quartermaster", class_name).replace("Three Spears", class_name)
            )
        for value in node.values():
            rename_visible_fields(value, class_name)
    elif isinstance(node, list):
        for item in node:
            rename_visible_fields(item, class_name)


def build_single_object(
    source_mod: dict[str, Any], class_data: dict[str, Any], image_url: str | None
) -> dict[str, Any]:
    class_name = class_data["class_name"]

    outer_template = find_quartermaster_outer(source_mod)
    clone = copy.deepcopy(outer_template)

    regenerate_guids(clone, seen=set())
    rename_visible_fields(clone, class_name)

    inner_box = find_inner_class_box(clone)
    inner_box["Nickname"] = class_name

    character_mat = find_character_mat(inner_box)
    character_mat["Nickname"] = f"Character Mat - {class_name}"
    custom_image = character_mat.get("CustomImage")
    if not isinstance(custom_image, dict):
        raise RuntimeError("Character Mat has no CustomImage object.")
    if image_url:
        custom_image["ImageURL"] = image_url

    for child in inner_box.get("ContainedObjects", []) or []:
        nick = child.get("Nickname")
        if isinstance(nick, str) and normalize(nick) == "character sheet":
            child["Nickname"] = f"Character Sheet - {class_name}"

    clone["Nickname"] = class_name
    return clone


def wrap_as_save(single_object: dict[str, Any], class_name: str) -> dict[str, Any]:
    # Minimal save wrapper so it can be loaded as its own save if needed.
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
        "--out-object",
        default="dist/Silent_Knife_saved_object.json",
        help="Output path for a single saved-object JSON.",
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_mod_path = Path(args.source_mod)
    class_data_path = Path(args.class_data)
    out_object_path = Path(args.out_object)
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

    single_object = build_single_object(source_mod, class_data, image_url)
    save_json(out_object_path, single_object)
    save_json(out_save_path, wrap_as_save(single_object, class_data["class_name"]))

    print(f"Wrote saved object: {out_object_path}")
    print(f"Wrote full save:    {out_save_path}")


if __name__ == "__main__":
    main()
