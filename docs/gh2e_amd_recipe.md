# GH2E AMD Recipe (Class-by-Class)

## Goal
Create a TTS-ready AMD setup for one GH2E class using:
1. a main AMD face atlas,
2. an extra-perk cards atlas (if needed),
3. a back image.

This is the exact approach used for Silent Knife.

## Source Of Truth (GH2E)
For **2nd edition perk requirements**, always use:
`assets/FH_compatible_sheets/*_character_sheet_front.png`

Do not treat GH1/worldhaven AMD sets as rules source; they are reference art sources only.

## Core Thinking
1. Convert perks into atomic operations: `remove`, `replace`, `add`.
2. Ignore pure removals for image work.
3. Build a list of **new face types** actually needed.
4. Reuse plain numeric cards (`+0`, `+1`, `+2`) whenever possible.
5. Only generate art for genuinely new face effects.

## Face Creation Tiers
1. `Reuse`: existing card already matches.
2. `Simple`: existing layout, only number/text tweak.
3. `Middle`: reuse existing effect icon/text pattern, but adapt to target class look.
4. `High`: new effect text/icon composition.

## Practical Workflow
1. Pick base style cards from the nearest GH1/GH2 class analog.
2. Pick donor cards for icon/effect/text fragments.
3. Generate one final master image per unique new face.
4. Duplicate masters to required copy counts.
5. Build atlas with exact tile dimensions expected by the target deck metadata.

## Final AMD Deck Layout Modes
Use one of these two layout modes based on the target JSON metadata.

1. Native mode (recommended):
- Atlas grid matches real class card pool exactly (example: `4x3` for 12 faces).
- Keep `NumWidth`/`NumHeight` and `DeckIDs` aligned to that native grid.

2. Legacy compatibility mode (Quartermaster-style):
- Build a `5x5` face atlas.
- Place real AMD faces first (row-major).
- Fill remaining unused slots with solid black filler tiles.
- Put the card back image in slot `24` (bottom-right).
- Keep `NumWidth=5`, `NumHeight=5`.

Critical rule:
- `DeckIDs` must only reference slots that contain real face cards.
- Do not reference filler slots, or black cards become drawable in-game.

## Extra Text Cards Recipe (Important)
For the extra cards (like Quartermaster `Perk 1/Perk 2/Extra Stock` style cards):
1. Start from an existing GH1 or GH2 extra/perk card image.
2. Text-edit only the content to match the new class.
3. Keep frame, typography style, and icon language consistent.
4. Normalize to target tile size before atlas assembly.

For Silent Knife this is automated by:
`python3 src/build_silent_knife_extra_perk_atlas.py`

## Silent Knife Active Outputs
1. Main AMD atlas:
`assets/final_class_amd_atlases/silent_knife_amd_atlas_4x3.png`
2. Extra cards atlas:
`assets/final_class_amd_atlases/silent_knife_extra_perks_atlas_2x2.png`
3. Back images:
`assets/final_class_amd_atlases/silent_knife_amd_back_814x530.png`
`assets/final_class_amd_atlases/silent_knife_amd_back_814x531.png`
4. Optional legacy-compatible 5x5 atlas:
`assets/final_class_amd_atlases/silent_knife_amd_atlas_5x5.png`
`assets/final_class_amd_atlases/silent_knife_amd_atlas_5x5_order.txt`

## Back Card Rule (TTS/GH2)
The back does not need to be embedded in the face atlas.
TTS uses `FaceURL` and `BackURL` separately.
Embedding the back as an unused tile can be convenient, but is optional.

## Repeat For Next Class
1. Create class-specific drop/input folders.
2. Generate final new faces.
3. Normalize tile dimensions.
4. Build atlas(es).
5. Wire `FaceURL`, `BackURL`, `NumWidth`, `NumHeight` in JSON.
