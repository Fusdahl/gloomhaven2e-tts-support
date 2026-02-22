#!/usr/bin/env python3
"""Validate GH2E character-mat image URLs and emit a JSON URL map.

The output JSON is intended to be consumed by build scripts.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = (
    "https://raw.githubusercontent.com/cmlenius/gloomhaven-card-browser/"
    "images/images/character-mats/gloomhaven-2nd-edition/"
)

# class_id -> card-browser slug
CLASS_SLUGS: dict[str, str] = {
    "bruiser": "bruiser",
    "cragheart": "cragheart",
    "mindthief": "mindthief",
    "spellweaver": "spellweaver",
    "tinkerer": "tinkerer",
    "berserker": "berserker",
    "bladeswarm": "bladeswarm",
    "doomstalker": "doomstalker",
    "elementalist": "elementalist",
    "nightshroud": "nightshroud",
    "plagueherald": "plagueherald",
    "quartermaster": "quartermaster",
    "sawbones": "sawbones",
    "sunkeeper": "sunkeeper",
    "soothsinger": "soothsinger",
    "wildfury": "wildfury",
    "soultether": "soultether",
    "silent_knife": "silentknife",
}

# Explicit per-class URL overrides when the gh2 slug path does not exist.
CLASS_URL_OVERRIDES: dict[str, str] = {
    "soultether": (
        "https://raw.githubusercontent.com/cmlenius/gloomhaven-card-browser/"
        "images/images/character-mats/gloomhaven/gh-summoner.jpeg"
    ),
}


def build_url(slug: str) -> str:
    return f"{BASE_URL}gh2-{slug}.jpeg"


def check_url(url: str, timeout_s: float) -> tuple[bool, int | None, str | None]:
    headers = {"User-Agent": "gh2e-tts-support-url-checker/1.0"}
    req = Request(url=url, method="HEAD", headers=headers)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return True, int(resp.status), None
    except HTTPError as err:
        # Some servers reject HEAD. Fall back to GET for those cases.
        if err.code in (403, 405, 501):
            get_req = Request(url=url, method="GET", headers=headers)
            try:
                with urlopen(get_req, timeout=timeout_s) as resp:
                    return True, int(resp.status), None
            except HTTPError as get_err:
                return False, int(get_err.code), str(get_err)
            except URLError as get_err:
                return False, None, str(get_err)
        return False, int(err.code), str(err)
    except URLError as err:
        return False, None, str(err)


def build_report(timeout_s: float) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    url_map: dict[str, str] = {}
    ok_map: dict[str, str] = {}

    for class_id, slug in CLASS_SLUGS.items():
        url = CLASS_URL_OVERRIDES.get(class_id, build_url(slug))
        ok, status, error = check_url(url, timeout_s=timeout_s)
        entries.append(
            {
                "class_id": class_id,
                "slug": slug,
                "url": url,
                "ok": ok,
                "status": status,
                "error": error,
            }
        )
        url_map[class_id] = url
        if ok:
            ok_map[class_id] = url

    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "base_url": BASE_URL,
        "total": len(entries),
        "ok_count": sum(1 for e in entries if e["ok"]),
        "failed_count": sum(1 for e in entries if not e["ok"]),
        "entries": entries,
        "url_map": url_map,
        "ok_url_map": ok_map,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="data/gh2_character_mat_urls.json",
        help="Path to write JSON report/map.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds.",
    )
    args = parser.parse_args()

    report = build_report(timeout_s=args.timeout)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Wrote: {output_path}")
    print(
        f"Checked {report['total']} URLs: "
        f"{report['ok_count']} OK, {report['failed_count']} failed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
