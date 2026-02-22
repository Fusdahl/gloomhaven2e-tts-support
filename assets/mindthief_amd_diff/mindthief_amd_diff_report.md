# Mindthief AMD Diff (Regenerated From GH2 Perks)

## Source Of Truth
- GH2 perk source: `assets/FH_compatible_sheets/vermling_mindthief_character_sheet_front.png`
- Reference only (not rules truth): GH1/worldhaven AMD image sets.

## Why This Rebuild
A prior diff pass used worldhaven/GH1 composition as if it represented GH2 perks. That was wrong for Mindthief.
This regenerated diff is based on the GH2 perk panel text from the FH-compatible sheet.

## GH2 AMD-Relevant Perk Lines
1. Replace two `(-1)` cards with one `(+0) "After the attack ability, control the target: Move 1"` card. (`x2`)
2. Replace one `(+0)` card with one `(+1) "Add +1 attack for each negative condition the target has"` card. (`x3`)
3. Replace one `(+0)` card with one `(+2)` card. (`x2`)
4. Add two `(+1) (Immobilize)` cards. (`x1` line => `2` cards)
5. Add one `(+2) [Infuse Ice]` card. (`x3`)
6. Add one `(Invisible, self) (Rolling)` card. (`x2`)
7. Ignore scenario effects and add one `(+1) (Rolling)` card. (`x1`)

Non-AMD perk lines are excluded from image work.

## Actionable Build Diff (2E target vs available GH1 assets)
`Reusable now`
1. `(+2)` plain: need `2`; reuse GH1 `136310`, `136311`.
2. `(+2) infuse ice`: need `3`; reuse GH1 `136312`, `136313`, then duplicate one.
3. `(+1) (Rolling)`: need `1`; reuse GH1 `136314/136315/136316/136317`.

`Needs new card creation`
1. `(+0) control target move 1`: need `2` (new text/effect face).
2. `(+1) add +1 attack per negative condition`: need `3` (new text/effect face).
3. `(+1) immobilize`: need `2` (new icon-effect face).
4. `(Invisible, self) (Rolling)`: need `2` (new icon-effect face).

## Notes
- Icon mapping confirmed by user:
  - `ICON_A` = `Immobilize`
  - Next perk lines map to `(Invisible, self) (Rolling)` and `(+1) (Rolling)`
- Next step is to create a Mindthief img2img pack mirroring Silent Knife structure, with one folder per new unique face.

## Files
- GH2 perk extraction CSV: `assets/mindthief_amd_diff/manifests/gh2_perk_requirements_from_fh_sheet.csv`
- Actionable diff CSV: `assets/mindthief_amd_diff/manifests/gh2_vs_gh1_actionable_diff.csv`
- Old worldhaven-based analysis archived in: `assets/mindthief_amd_diff/_archive_worldhaven_basis/`
