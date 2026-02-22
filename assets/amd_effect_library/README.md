# AMD Effect Library Foundation

This folder combines reusable attack modifier card images from:
- GH1 full class mod JSON (high-confidence text descriptions)
- GH2 3-class mod JSON (high-confidence text descriptions)
- worldhaven attack modifier image sets for Gloomhaven + Frosthaven classes
  (code-level descriptors via xws/name when card text is not explicit).

## Main outputs
- `cards/by_class/...` grouped by source/expansion/class
- `cards/by_effect/...` grouped by normalized effect key
- `manifests/cards.csv` all card records
- `manifests/effects.csv` grouped effect summary
- `manifests/source_summary.json` aggregate counts

## Confidence levels
- `high`: effect text directly from TTS mod card nickname
- `code`: effect keyed by xws/name code (image reuse source; text may need validation)