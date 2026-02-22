#!/usr/bin/env python3
"""Build a reusable AMD effect foundation from local mod JSONs + worldhaven.

Outputs:
- assets/amd_effect_library/cards/by_class/...
- assets/amd_effect_library/cards/by_effect/...
- assets/amd_effect_library/manifests/cards.csv
- assets/amd_effect_library/manifests/effects.csv
- assets/amd_effect_library/manifests/source_summary.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "amd_effect_library"

GH1_MOD_PATH = ROOT / "original_mod_json" / "Gloomhaven  all character 1st edition.json"
GH2_MOD_PATH = ROOT / "original_mod_json" / "Gloomhaven 2e classes  mod.json"
CHARACTERS_TS = ROOT.parent / "gloomhaven-card-browser" / "data" / "characters.ts"

WORLDHAVEN_AM_JS_URL = (
    "https://raw.githubusercontent.com/any2cards/worldhaven/master/data/attack-modifiers.js"
)
WORLDHAVEN_RAW_BASE = "https://raw.githubusercontent.com/any2cards/worldhaven/master/images/"
WORLDHAVEN_EXPANSIONS = {"gloomhaven", "frosthaven"}
WORLDHAVEN_SOURCE_KEY = "worldhaven"
DOWNLOAD_MISSES: list[tuple[str, str]] = []


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True).strip()


def run_quiet(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_") or "unknown"


def normalize_effect_text(effect_text: str) -> str:
    t = effect_text.strip()
    t = re.sub(r"^\s*attack\s+modifier\s*", "", t, flags=re.I)
    t = t.replace("−", "-")
    t = t.replace("×", "x")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    mkdir(dest.parent)
    cmd = [
        "curl",
        "-L",
        "--fail",
        "--retry",
        "2",
        "--retry-delay",
        "1",
        "--connect-timeout",
        "8",
        "--max-time",
        "30",
        "-o",
        str(dest),
        url,
    ]
    try:
        run_quiet(cmd)
        return True
    except Exception:
        DOWNLOAD_MISSES.append((url, str(dest)))
        return False


def identify_size(image: Path) -> tuple[int, int]:
    w_h = run(["magick", "identify", "-format", "%w %h", str(image)])
    w, h = w_h.split()
    return int(w), int(h)


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_if_missing(src: Path, dst: Path) -> None:
    mkdir(dst.parent)
    if not dst.exists():
        shutil.copy2(src, dst)


def class_name_map_from_characters_ts() -> dict[str, str]:
    if not CHARACTERS_TS.exists():
        return {}
    text = CHARACTERS_TS.read_text(encoding="utf-8")
    class_re = re.compile(r'class:\s*"([^"]+)"')
    name_re = re.compile(r'name:\s*"([^"]+)"')
    lines = text.splitlines()
    mapping: dict[str, str] = {}
    for i, line in enumerate(lines):
        m = class_re.search(line)
        if not m:
            continue
        code = m.group(1)
        name = ""
        for j in range(i + 1, min(i + 12, len(lines))):
            nm = name_re.search(lines[j])
            if nm:
                name = nm.group(1)
                break
        if name:
            mapping[code.lower()] = name
    return mapping


def crop_card_from_atlas(
    atlas_path: Path,
    num_w: int,
    num_h: int,
    card_index: int,
    out_path: Path,
) -> bool:
    atlas_w, atlas_h = identify_size(atlas_path)
    tile_w = atlas_w // num_w
    tile_h = atlas_h // num_h
    col = card_index % num_w
    row = card_index // num_w
    x = col * tile_w
    y = row * tile_h
    if row >= num_h:
        return False
    mkdir(out_path.parent)
    run_quiet(
        [
            "magick",
            str(atlas_path),
            "-crop",
            f"{tile_w}x{tile_h}+{x}+{y}",
            "+repage",
            str(out_path),
        ]
    )
    return True


def extract_amd_decks_from_mod(mod_path: Path, source_key: str) -> list[dict[str, Any]]:
    data = json.loads(mod_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    source_atlas_dir = OUT / "sources" / source_key / "atlases"
    class_dir_base = OUT / "cards" / "by_class" / source_key
    mkdir(source_atlas_dir)
    mkdir(class_dir_base)

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            contained = obj.get("ContainedObjects")
            nick = (obj.get("Nickname") or "").strip()
            if isinstance(contained, list):
                amd_decks = [
                    c
                    for c in contained
                    if isinstance(c, dict)
                    and (c.get("Nickname") or "").strip() == "Attack Modifiers"
                    and isinstance(c.get("CustomDeck"), dict)
                ]
                for amd in amd_decks:
                    process_amd_deck(amd, nick)
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    def process_amd_deck(amd: dict[str, Any], class_name: str) -> None:
        class_slug = slugify(class_name or "unknown_class")
        custom_deck = {
            int(k): v for k, v in amd.get("CustomDeck", {}).items() if isinstance(v, dict)
        }
        atlas_cache: dict[int, Path] = {}
        dims_cache: dict[int, tuple[int, int]] = {}

        for deck_id, deck_info in custom_deck.items():
            face_url = deck_info.get("FaceURL")
            if not face_url:
                continue
            atlas_path = source_atlas_dir / f"deck_{deck_id}_face.png"
            if not download(face_url, atlas_path):
                continue
            atlas_cache[deck_id] = atlas_path
            dims_cache[deck_id] = (
                int(deck_info.get("NumWidth") or 1),
                int(deck_info.get("NumHeight") or 1),
            )

        for card_obj in amd.get("ContainedObjects", []):
            if not isinstance(card_obj, dict):
                continue
            card_id = card_obj.get("CardID")
            if not isinstance(card_id, int):
                continue
            deck_id = card_id // 100
            card_index = card_id % 100
            if deck_id not in atlas_cache:
                continue
            num_w, num_h = dims_cache[deck_id]
            card_nick = (card_obj.get("Nickname") or "").strip()
            effect_text = normalize_effect_text(card_nick)
            effect_key = f"text__{slugify(effect_text)}" if effect_text else f"id__{card_id}"
            out_img = (
                class_dir_base
                / class_slug
                / f"{card_id:06d}_{slugify(card_nick or f'card_{card_id}')}.png"
            )
            ok = crop_card_from_atlas(
                atlas_cache[deck_id],
                num_w,
                num_h,
                card_index,
                out_img,
            )
            if not ok:
                continue
            rows.append(
                {
                    "source": source_key,
                    "expansion": "gloomhaven",
                    "class_key": class_slug,
                    "class_name": class_name,
                    "effect_text": effect_text,
                    "effect_key": effect_key,
                    "effect_confidence": "high",
                    "descriptor": card_nick,
                    "deck_id": str(deck_id),
                    "card_id": str(card_id),
                    "xws": "",
                    "image_path": str(out_img.relative_to(OUT)),
                }
            )

    walk(data)
    return rows


def load_worldhaven_attack_modifiers() -> list[dict[str, Any]]:
    js_path = OUT / "sources" / "worldhaven" / "attack-modifiers.js"
    ok = download(WORLDHAVEN_AM_JS_URL, js_path)
    if not ok:
        raise RuntimeError("Failed to download worldhaven attack-modifiers.js")
    return json.loads(js_path.read_text(encoding="utf-8"))


def extract_worldhaven_class_cards() -> list[dict[str, Any]]:
    entries = load_worldhaven_attack_modifiers()
    class_name_map = class_name_map_from_characters_ts()
    rows: list[dict[str, Any]] = []
    by_class_dir = OUT / "cards" / "by_class" / WORLDHAVEN_SOURCE_KEY
    source_img_dir = OUT / "sources" / "worldhaven" / "images"
    mkdir(by_class_dir)

    seen_image_paths: set[str] = set()
    for e in entries:
        image_rel = (e.get("image") or "").strip()
        expansion = (e.get("expansion") or "").strip().lower()
        if expansion not in WORLDHAVEN_EXPANSIONS:
            continue
        if "/base/" in image_rel:
            continue
        m = re.match(r"attack-modifiers/([^/]+)/([^/]+)/([^/]+\.png)$", image_rel)
        if not m:
            continue
        exp_from_path, class_code, filename = m.groups()
        if exp_from_path != expansion:
            continue
        if len(class_code) != 2:
            continue
        # JS contains duplicate logical rows per image; keep one physical card image row.
        if image_rel in seen_image_paths:
            continue
        seen_image_paths.add(image_rel)

        raw_url = WORLDHAVEN_RAW_BASE + image_rel
        local_source = source_img_dir / image_rel
        if not download(raw_url, local_source):
            continue

        class_key = class_code.lower()
        class_name = class_name_map.get(class_key, class_key.upper())
        card_name = (e.get("name") or "").strip()
        xws = (e.get("xws") or "").strip()
        effect_text = ""
        # Use human text when present; fallback to xws/code descriptors.
        if card_name and not re.fullmatch(r"\d+", card_name):
            effect_text = card_name
        effect_key = f"xws__{slugify(xws)}" if xws else f"code__{slugify(card_name)}"

        out_img = (
            by_class_dir
            / expansion
            / class_key
            / f"{slugify(filename.replace('.png', ''))}.png"
        )
        copy_if_missing(local_source, out_img)
        rows.append(
            {
                "source": WORLDHAVEN_SOURCE_KEY,
                "expansion": expansion,
                "class_key": class_key,
                "class_name": class_name,
                "effect_text": effect_text,
                "effect_key": effect_key,
                "effect_confidence": "code",
                "descriptor": card_name,
                "deck_id": "",
                "card_id": "",
                "xws": xws,
                "image_path": str(out_img.relative_to(OUT)),
            }
        )
    return rows


def build_by_effect(rows: list[dict[str, Any]]) -> None:
    effect_base = OUT / "cards" / "by_effect"
    mkdir(effect_base)
    for i, r in enumerate(rows, start=1):
        key = r["effect_key"] or "unknown"
        dst_dir = effect_base / key
        src_img = OUT / r["image_path"]
        stem = f"{i:05d}_{slugify(r['source'])}_{slugify(r['class_key'])}"
        dst_img = dst_dir / f"{stem}.png"
        copy_if_missing(src_img, dst_img)


def write_manifests(rows: list[dict[str, Any]]) -> None:
    manifest_dir = OUT / "manifests"
    mkdir(manifest_dir)
    for r in rows:
        img_abs = OUT / r["image_path"]
        r["image_sha1"] = sha1_file(img_abs) if img_abs.exists() else ""

    rows_sorted = sorted(
        rows,
        key=lambda r: (
            r["source"],
            r["expansion"],
            r["class_key"],
            r["effect_key"],
            r["image_path"],
        ),
    )

    cards_csv = manifest_dir / "cards.csv"
    fieldnames = [
        "source",
        "expansion",
        "class_key",
        "class_name",
        "effect_text",
        "effect_key",
        "effect_confidence",
        "descriptor",
        "deck_id",
        "card_id",
        "xws",
        "image_path",
        "image_sha1",
    ]
    with cards_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_sorted)

    effect_counter: Counter[str] = Counter(r["effect_key"] for r in rows_sorted)
    effect_sources: dict[str, set[str]] = defaultdict(set)
    effect_classes: dict[str, set[str]] = defaultdict(set)
    for r in rows_sorted:
        k = r["effect_key"]
        effect_sources[k].add(r["source"])
        effect_classes[k].add(r["class_key"])

    effects_csv = manifest_dir / "effects.csv"
    with effects_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["effect_key", "count", "sources", "class_count", "example_effect_text"]
        )
        for k in sorted(effect_counter):
            sample_text = next((r["effect_text"] for r in rows_sorted if r["effect_key"] == k), "")
            writer.writerow(
                [
                    k,
                    effect_counter[k],
                    ";".join(sorted(effect_sources[k])),
                    len(effect_classes[k]),
                    sample_text,
                ]
            )

    summary = {
        "total_cards": len(rows_sorted),
        "by_source": Counter(r["source"] for r in rows_sorted),
        "by_expansion": Counter(r["expansion"] for r in rows_sorted),
        "by_confidence": Counter(r["effect_confidence"] for r in rows_sorted),
        "unique_effect_keys": len(effect_counter),
    }
    (manifest_dir / "source_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    missing_csv = manifest_dir / "missing_images.csv"
    with missing_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "dest"])
        for url, dest in DOWNLOAD_MISSES:
            writer.writerow([url, dest])


def write_readme() -> None:
    readme = OUT / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# AMD Effect Library Foundation",
                "",
                "This folder combines reusable attack modifier card images from:",
                "- GH1 full class mod JSON (high-confidence text descriptions)",
                "- GH2 3-class mod JSON (high-confidence text descriptions)",
                "- worldhaven attack modifier image sets for Gloomhaven + Frosthaven classes",
                "  (code-level descriptors via xws/name when card text is not explicit).",
                "",
                "## Main outputs",
                "- `cards/by_class/...` grouped by source/expansion/class",
                "- `cards/by_effect/...` grouped by normalized effect key",
                "- `manifests/cards.csv` all card records",
                "- `manifests/effects.csv` grouped effect summary",
                "- `manifests/source_summary.json` aggregate counts",
                "",
                "## Confidence levels",
                "- `high`: effect text directly from TTS mod card nickname",
                "- `code`: effect keyed by xws/name code (image reuse source; text may need validation)",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    mkdir(OUT)
    by_effect = OUT / "cards" / "by_effect"
    manifests = OUT / "manifests"
    if by_effect.exists():
        shutil.rmtree(by_effect)
    if manifests.exists():
        shutil.rmtree(manifests)
    rows: list[dict[str, Any]] = []
    rows.extend(extract_amd_decks_from_mod(GH1_MOD_PATH, "gh1_mod_json"))
    rows.extend(extract_amd_decks_from_mod(GH2_MOD_PATH, "gh2_mod_json"))
    rows.extend(extract_worldhaven_class_cards())
    build_by_effect(rows)
    write_manifests(rows)
    write_readme()
    print(f"Built AMD effect library at: {OUT}")
    print(f"Total cards: {len(rows)}")


if __name__ == "__main__":
    main()
