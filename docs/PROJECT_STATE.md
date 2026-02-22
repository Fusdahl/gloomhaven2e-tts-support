# GH2E TTS Project State

Last updated: 2026-02-22

## Current Working Outputs
- Main file to load in TTS Saved Objects:
  - `dist/Silent_Knife_saved_object_v2_testable.json`
- Related generated files:
  - `dist/Silent_Knife_save_v2_testable.json`
  - `dist/Silent_Knife_object_state_v2_testable.json`

## What We Changed Recently
- Fixed Saved Object format issue that caused:
  - `Error converting value True to type GridState line 35 position 14`
- Added a URL checker for GH2 character mats:
  - `src/check_character_mat_urls.py`
- Verified and saved a class -> source URL map:
  - `data/gh2_character_mat_urls.json`
- Added Soultether override to use Summoner mat URL (since `gh2-soultether.jpeg` was 404).
- Downloaded all 18 character mats into:
  - `assets/final_character_mats/`
- Added repo-hosted class -> final mat URL map:
  - `data/final_character_mat_repo_urls.json`
- Updated Silent Knife builder to reference repo-hosted final mat image for Character Mat:
  - `src/build_silent_knife_test_object.py`
  - URL used:
    - `https://raw.githubusercontent.com/Fusdahl/gloomhaven2e-tts-support/main/assets/final_character_mats/silent_knife_character_mat.jpeg`

## Silent Knife Build Behavior (Current)
- Uses FH-compatible character sheet front/back:
  - `assets/FH_compatible_sheets/silent_knife_character_sheet_front.png`
  - `assets/FH_compatible_sheets/silent_knife_character_sheet_back.png`
- Uses Silent Knife final ability atlas and back:
  - `assets/final_class_ability_atlases/silent_knife_ability_atlas.png`
  - `assets/final_class_ability_atlases/silent_knife_ability_back.png`
- Uses Silent Knife AMD atlas + back:
  - `assets/final_class_amd_atlases/silent_knife_amd_atlas_5x5.png`
  - `assets/final_class_amd_atlases/silent_knife_amd_back_814x531.png`
- Uses Silent Knife extra-perk atlas:
  - `assets/final_class_amd_atlases/silent_knife_extra_perks_atlas_2x2.png`
- Class script patches applied in builder include:
  - Silent Knife HP progression: `8, 9, 11, 12, 14, 15, 17, 18, 20`
  - Ability name/level/initiative map from:
    - `assets/silent_knife_asset_downloads/ordered_for_rows/ORDER.txt`
  - Perk transformations disabled for now (manual AMD handling path).

## Character Mat Strategy
- Canonical local/final folder:
  - `assets/final_character_mats/`
- Naming scheme:
  - `<class_id>_character_mat.jpeg`
- Repo URL pattern:
  - `https://raw.githubusercontent.com/Fusdahl/gloomhaven2e-tts-support/main/assets/final_character_mats/<class_id>_character_mat.jpeg`

## Known Risks / Open Items
- `saved_object_v2_testable` and `save_v2_testable` can diverge if regenerated from different inputs.
- Need to keep using the wrapped saved object file for TTS Saved Objects:
  - Use `dist/Silent_Knife_saved_object_v2_testable.json`
  - Do not load `dist/Silent_Knife_object_state_v2_testable.json` directly as a saved object.
- Perk transformation logic is intentionally disabled right now; manual AMD deck edits are expected.

## Standard Rebuild Commands
- Rebuild URL map:
  - `python3 src/check_character_mat_urls.py --output data/gh2_character_mat_urls.json --timeout 15`
- Rebuild Silent Knife v2 outputs:
  - `python3 src/build_silent_knife_test_object.py --input dist/Silent_Knife_save.json --output dist/Silent_Knife_save_v2_testable.json`
  - `python3 src/build_silent_knife_test_object.py --input dist/Silent_Knife_save_v2_testable.json --output dist/Silent_Knife_saved_object_v2_testable.json`
  - `python3 src/build_silent_knife_test_object.py --input dist/Silent_Knife_save_v2_testable.json --output dist/Silent_Knife_object_state_v2_testable.json`

## Next Steps
- Confirm in TTS that Character Mat now loads from final repo URL and appears correctly.
- Decide if Character Mat should remain as an object in class bag or be pruned in final release.
- Apply same final-character-mat wiring approach to additional classes beyond Silent Knife.
- If desired, re-enable and rework perk transformations class-by-class after AMD assets are finalized.
