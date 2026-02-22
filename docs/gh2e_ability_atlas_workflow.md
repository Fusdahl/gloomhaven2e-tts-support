# GH2E Ability Atlas Workflow (Descriptive E2E)

## Purpose
Create class ability atlases for Gloomhaven 2nd Edition classes in a way that is repeatable, but flexible enough for class-specific differences (card count, extra mechanics, deck structure).

This document describes **what needs to happen** end-to-end, not one rigid implementation.

## Expected Outputs Per Class
- A local working folder with downloaded source images.
- One or more composed atlas images (fronts, and usually a back).
- A manifest of card order used to build the atlas.
- Enough metadata to wire the atlas into TTS JSON later (dimensions, slot count, back handling).

## Inputs You Need
- A source-of-truth card list for GH2E class abilities (for example, `gloomhaven-card-browser` data files).
- A reference atlas from an existing mod (to match layout conventions where needed).
- A local image composition toolchain (ImageMagick is fine).
- A target class identifier (for example, `SC2` for Silent Knife in GH2 naming).

## Phase 1: Discover Class Data and Constraints
For each class, confirm:
- Class code and class name mapping.
- Total number of ability cards.
- Card names, levels, initiatives, and image paths.
- Whether the class has extra non-standard cards that should not be packed into the same atlas.

Why this matters:
- Not all classes have the same number of total cards.
- Some classes can require separate handling for extras (for example, mechanic-specific cards/decks).

## Phase 2: Download Assets (E2E Includes This)
Create a class-specific asset folder and save:
- All front card images for that class.
- The reference back image or back slot source.
- A text file of URLs used (`urls.txt`).

Recommended artifact structure:
- `raw/` downloaded originals
- `ordered/` renamed/copied in build order
- `build/` generated atlas outputs
- `manifests/` order files and notes

## Phase 3: Decide Atlas Layout Per Class
Do not assume every class is 28 cards.

Decide, class-by-class:
- Number of columns and rows.
- Whether to preserve a legacy layout (example: 8x4 with filler slots and a back slot).
- Whether to split into multiple atlases if card count exceeds a practical layout.
- Whether TTS integration expects exact dimensions from a reference mod.

For the Scoundrel -> Silent Knife example:
- Legacy-compatible layout was used.
- Front slots were replaced with GH2 fronts.
- Remaining bottom-row slots were black filler + back card slot.

## Phase 4: Define Card Ordering
Create an explicit manifest for slot order.  
Example ordering strategy:
- Level 1 first
- Level X next
- Then levels 2 to 9
- Within each level group, lowest initiative first

Keep this manifest per class so atlas generation and TTS mapping remain auditable.

## Phase 5: Compose Atlas
When composing:
- Use consistent card cell dimensions.
- Use zero padding/gaps unless a target mod requires spacing.
- Apply filler/back slot rules based on the chosen layout.
- Export a lossless working atlas (PNG) first.

If matching an existing atlas format:
- Match final width/height.
- Match slot geometry.
- Match where black filler and back slots are located.

## Phase 6: Validate Before TTS Integration
Verify:
- Atlas dimensions and format.
- Card count actually placed.
- Slot order matches manifest.
- Back slot is correct.
- No accidental scaling distortion.

Useful checks:
- Crop sample slots and verify expected card names visually.
- Confirm filler slots are truly black/empty if required.
- Keep a quick side-by-side with the original reference atlas.

## Phase 7: Prepare for TTS Wiring
Capture the values you will need in JSON:
- `FaceURL` target (where atlas will be hosted).
- `BackURL` target.
- `NumWidth`/`NumHeight` (atlas grid dimensions).
- `DeckIDs` and slot mapping aligned with your chosen order.

Important:
- If a class uses multiple decks (starting/advanced/extras), map each deck explicitly.
- Treat atlas generation and TTS deck wiring as separate steps so debugging is easier.

## Class-to-Class Variability Guidelines
When classes differ from the Scoundrel pattern:
- Keep the same pipeline phases.
- Change only the data and layout decisions.
- Document exceptions in the class manifest (why layout or slot behavior changed).

This keeps the workflow stable while allowing class-specific handling.

## Suggested Per-Class Checklist
- [ ] Confirm class code and source card list.
- [ ] Download all required front images.
- [ ] Download/prepare back image source.
- [ ] Decide layout for this class (rows/cols, split or not).
- [ ] Generate slot-order manifest.
- [ ] Build atlas image(s).
- [ ] Validate slot content and dimensions.
- [ ] Record values needed for TTS JSON wiring.

