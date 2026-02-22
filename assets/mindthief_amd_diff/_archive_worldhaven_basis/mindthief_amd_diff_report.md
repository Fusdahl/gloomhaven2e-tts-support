# Mindthief AMD Diff (GH1 -> GH2 target)

## GH2E Perk Source Rule
For 2nd edition, perk requirements must be read from:
`assets/FH_compatible_sheets/vermling_mindthief_character_sheet_front.png`

GH1/worldhaven assets are reference art sources, not authoritative rules sources.

## Scope
- GH1 source cards: `assets/amd_effect_library/cards/by_class/gh1_mod_json/mindthief/`
- Target cards used for GH2 prep: `assets/worldhaven_attack_modifiers_gloomhaven/mindthief/`
- Mapping method: nearest-image MAE after size normalization (300x196)

## Result
- Target AMD deck has 20 face cards + 1 back card.
- Mechanical composition matches GH1 Mindthief card-effect set (no new effect types detected).
- Practical diff is style/art-level, not rules-level, based on this mapping.

## Effect Count Diff
Target counts inferred from mapped cards:
- `(+0) (Muddle) (Rolling)`: `4`
- `(+1) (Rolling)`: `4`
- `(+0) (Push 1) (Rolling)`: `3`
- `(+0) (Immobilize) (Rolling)`: `2`
- `(+2)`: `2`
- `(+2) (Infuse Ice)`: `2`
- `(+0)`: `1`
- `(+0) (Disarm) (Rolling)`: `1`
- `(+0) (Stun) (Rolling)`: `1`

## What You Need To Create
1. If you accept worldhaven as final art: no img2img transformations required; use target cards directly.
2. If you want custom style harmonization: create style-converted versions for the same 9 unique effect faces above, then duplicate by counts.

## Files
- Enriched card mapping: `assets/mindthief_amd_diff/manifests/worldhaven_to_gh1_mapping_enriched.csv`
- Effect summary: `assets/mindthief_amd_diff/manifests/effect_summary.csv`
- Target contact sheet: `assets/mindthief_amd_diff/contacts/target_worldhaven_mindthief_contact.png`
- Source contact sheet: `assets/mindthief_amd_diff/contacts/source_gh1_mindthief_contact.png`
- Normalized back image: `assets/mindthief_amd_diff/mindthief_amd_back_814x531.png`
