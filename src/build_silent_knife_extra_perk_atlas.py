#!/usr/bin/env python3
"""Build Silent Knife extra-perk atlas (2x2) from 3 user-provided cards.

Workflow:
1) Read 3 card images from input dir.
2) Normalize each to 814x530 (Quartermaster perk-card tile size).
3) Build a 2x2 atlas with the 3 cards + a preserved filler tile from
   Quartermaster's deck_5021_face slot 3 (bottom-right).
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_DIR = (
    ROOT
    / "assets"
    / "silent_knife_amd_img2img"
    / "transformation_input_pack_v2"
    / "05_extra_text_cards_drop_here"
)
DEFAULT_OUTPUT_ATLAS = (
    ROOT / "assets" / "final_class_amd_atlases" / "silent_knife_extra_perks_atlas_2x2.png"
)
DEFAULT_OUTPUT_ORDER = (
    ROOT
    / "assets"
    / "final_class_amd_atlases"
    / "silent_knife_extra_perks_atlas_2x2_order.txt"
)
DEFAULT_REFERENCE_ATLAS = (
    ROOT / "assets" / "amd_effect_library" / "sources" / "gh2_mod_json" / "atlases" / "deck_5021_face.png"
)
DEFAULT_SILENT_KNIFE_BACK = (
    ROOT
    / "assets"
    / "worldhaven_attack_modifiers_gloomhaven"
    / "silent_knife"
    / "gh_am_silent_knife_back.png"
)

TARGET_W = 814
TARGET_H = 530


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def normalize_card(src: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Fill target area while preserving aspect ratio, then center crop.
    run(
        [
            "magick",
            str(src),
            "-gravity",
            "center",
            "-resize",
            f"{TARGET_W}x{TARGET_H}^",
            "-crop",
            f"{TARGET_W}x{TARGET_H}+0+0",
            "+repage",
            str(out),
        ]
    )


def extract_reference_tile_3(reference_atlas: Path, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # deck_5021_face is 2x2 tiles. Tile index 3 is bottom-right.
    run(
        [
            "magick",
            str(reference_atlas),
            "-crop",
            f"{TARGET_W}x{TARGET_H}+{TARGET_W}+{TARGET_H}",
            "+repage",
            str(out),
        ]
    )


def list_input_cards(input_dir: Path) -> list[Path]:
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    cards = []
    for p in sorted(input_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in exts:
            continue
        name = p.name.lower()
        if name.startswith("reference_"):
            continue
        if name.startswith("template_"):
            continue
        cards.append(p)
    return cards


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-atlas", type=Path, default=DEFAULT_OUTPUT_ATLAS)
    parser.add_argument("--output-order", type=Path, default=DEFAULT_OUTPUT_ORDER)
    parser.add_argument("--reference-atlas", type=Path, default=DEFAULT_REFERENCE_ATLAS)
    parser.add_argument("--back-image", type=Path, default=DEFAULT_SILENT_KNIFE_BACK)
    args = parser.parse_args()

    input_dir: Path = args.input_dir
    if not input_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {input_dir}")

    cards = list_input_cards(input_dir)
    if len(cards) != 3:
        raise RuntimeError(
            f"Expected exactly 3 input card images in {input_dir}, found {len(cards)}."
        )

    tmp = ROOT / "dist" / "_silent_knife_extra_perk_build"
    if tmp.exists():
        for p in tmp.glob("*"):
            p.unlink()
    tmp.mkdir(parents=True, exist_ok=True)

    normalized = []
    for i, src in enumerate(cards):
        out = tmp / f"{i:02d}_{src.stem}_norm.png"
        normalize_card(src, out)
        normalized.append(out)

    filler = tmp / "03_back_tile.png"
    if args.back_image.exists():
        normalize_card(args.back_image, filler)
        filler_label = f"silent_knife_back ({args.back_image.name})"
    else:
        extract_reference_tile_3(args.reference_atlas, filler)
        filler_label = "reference filler tile from quartermaster deck_5021_face (bottom-right)"

    args.output_atlas.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            "magick",
            "montage",
            str(normalized[0]),
            str(normalized[1]),
            str(normalized[2]),
            str(filler),
            "-mode",
            "concatenate",
            "-tile",
            "2x2",
            str(args.output_atlas),
        ]
    )

    args.output_order.parent.mkdir(parents=True, exist_ok=True)
    args.output_order.write_text(
        "\n".join(
            [
                "Silent Knife extra perks atlas order (2x2, left-to-right, top-to-bottom)",
                "",
                f"00: {cards[0].name}",
                f"01: {cards[1].name}",
                f"02: {cards[2].name}",
                f"03: {filler_label}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"Built atlas: {args.output_atlas}")
    print(f"Wrote order: {args.output_order}")


if __name__ == "__main__":
    main()
