#!/usr/bin/env python3
"""Sync sheet click-map positions into data/class_profiles.json.

Usage:
  python3 src/sync_sheet_positions.py
  python3 src/sync_sheet_positions.py --class-id bruiser
  python3 src/sync_sheet_positions.py --dry-run
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_PROFILES = Path("data/class_profiles.json")
DEFAULT_POSITIONS = Path("data/class_sheet_positions.json")


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _valid_positions(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for row in value:
        if not isinstance(row, list) or len(row) != 2:
            return False
        if not all(isinstance(n, int) for n in row):
            return False
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES, help="Target class profiles JSON.")
    parser.add_argument("--positions", type=Path, default=DEFAULT_POSITIONS, help="Source sheet positions JSON.")
    parser.add_argument("--class-id", default=None, help="Optional single class id to sync.")
    parser.add_argument("--dry-run", action="store_true", help="Show updates without writing.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    profiles_data = _load_json(args.profiles)
    positions_data = _load_json(args.positions)

    profile_classes = profiles_data.get("classes")
    position_classes = positions_data.get("classes")
    if not isinstance(profile_classes, dict):
        raise RuntimeError(f"Invalid profiles format in {args.profiles}")
    if not isinstance(position_classes, dict):
        raise RuntimeError(f"Invalid positions format in {args.positions}")

    wanted = {args.class_id} if args.class_id else None
    updated: list[str] = []
    skipped_empty: list[str] = []
    skipped_missing_profile: list[str] = []

    for class_id, pos in position_classes.items():
        if wanted and class_id not in wanted:
            continue
        if not isinstance(pos, dict):
            continue

        perk_positions = pos.get("perk_positions")
        mastery_positions = pos.get("mastery_positions")
        if not _valid_positions(perk_positions) or not _valid_positions(mastery_positions):
            skipped_empty.append(class_id)
            continue

        profile = profile_classes.get(class_id)
        if not isinstance(profile, dict):
            skipped_missing_profile.append(class_id)
            continue

        changed = False
        if profile.get("perk_positions") != perk_positions:
            profile["perk_positions"] = perk_positions
            changed = True
        if profile.get("mastery_positions") != mastery_positions:
            profile["mastery_positions"] = mastery_positions
            changed = True
        if changed:
            updated.append(class_id)

    print(f"Updated classes: {', '.join(updated) if updated else '(none)'}")
    if skipped_empty:
        print(f"Skipped (empty/invalid positions): {', '.join(skipped_empty)}")
    if skipped_missing_profile:
        print(f"Skipped (class missing in profiles): {', '.join(skipped_missing_profile)}")

    if not args.dry_run and updated:
        _save_json(args.profiles, profiles_data)
        print(f"Wrote {args.profiles}")
    elif args.dry_run:
        print("Dry-run only, no files written.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
