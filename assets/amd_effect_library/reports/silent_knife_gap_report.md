# Silent Knife AMD Build Notes (Simplified)

## Goal
Only track **new AMD faces to create**. Ignore removals and direct reuses unless needed as source material.

Primary source sheet:
`assets/FH_compatible_sheets/silent_knife_character_sheet_front.png`

## No Work Needed
1. Pure removals (`-2`, `-1`) need no new image files.
2. Plain `(+2)` replacements can reuse GH1 Scoundrel `(+2)` cards.
3. Plain `(+1)` replacements can reuse GH1 Scoundrel `(+1)` card.

## New Faces To Create
These are the only art-generation tasks needed for the Silent Knife AMD set.

1. `(+1) disarm` face.
Perk solved: `Add one (+1) [effect icon] card` (assuming this icon resolves to disarm).
Suggested count: `2` copies.

2. `(+1) money-token conditional` face.
Perk solved: `Replace one (+0) card with one (+1) "Gain one money token if this attack targeted an adjacent enemy" card`.
Suggested count: `3` copies (`+1` optional extra if desired).

3. `(+1) invisible/self-style` face from `137816`.
Perk solved: `Replace one (+1) card with one (+1) [effect], self [self icon] card`.
Suggested count: `2` copies.
Workflow: first normalize `137816` to regular scoundrel green style, then change value to `+1`.

## Transformation Input Folder
Prepared source files are here:
`assets/silent_knife_amd_img2img/transformation_input_pack_v2`

### 01 disarm
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/01_disarm_plus1/BASE_scoundrel_plus1.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/01_disarm_plus1/DONOR_gh1_plus1_disarm.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/01_disarm_plus1/ALT_DONOR_gh1_plus0_disarm_rolling.png`

### 02 money token
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/02_money_token_plus1/BASE_scoundrel_plus1.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/02_money_token_plus1/REF_silent_knife_perks_zoom.png`

### 03 invisible/self
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/03_invisible_plus1_self/BASE_scoundrel_plus0_invisible_rolling.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/03_invisible_plus1_self/DONOR_scoundrel_green_rolling_style.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/03_invisible_plus1_self/ALT_DONOR_scoundrel_plus1.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/03_invisible_plus1_self/REF_silent_knife_perks_zoom.png`

### 04 direct reuse
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/04_reuse_no_edit/REUSE_plus1.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/04_reuse_no_edit/REUSE_plus2_A.png`
`assets/silent_knife_amd_img2img/transformation_input_pack_v2/04_reuse_no_edit/REUSE_plus2_B.png`

## Reusable Thinking For Other Classes
1. Parse perks into `remove`, `replace`, and `add`.
2. Drop `remove` from image workload immediately.
3. Reuse plain numeric cards first (`+0`, `+1`, `+2`) if already available.
4. Only generate **new unique face effects** that are not exact reuses.
5. For each new face, define:
base card (target class style) + donor card (icon/text payload) + final copy count.
