# Silent Knife AMD img2img workflow

## Goal
Create new Silent Knife attack modifier card images using Scoundrel 1E cards as visual reference, while updating text/icons to match Silent Knife perks.

## Inputs for each generation task
- Primary reference image: one card from `transform_tasks/<task>/`
- Rules source: `source_silent_knife/silent_knife_perks_panel_zoom.png`
- Task target spec: `transform_tasks/<task>/TARGET.txt`
- Prompt template: `transform_tasks/<task>/PROMPT_TEMPLATE.txt`

## Recommended prompt pattern
1. Paste `PROMPT_TEMPLATE.txt`.
2. Add: "Use attached reference card as the exact style template."
3. Add exact target text from `TARGET.txt`.
4. Add icon guidance from the perks panel crop.
5. Ask for one card output only, same aspect ratio.

## Suggested output naming
- `silent_knife_amd_<task>_<nn>.png`
- Example: `silent_knife_amd_money_token_01.png`

## Assembly notes
- Keep as-is candidates are in `keep_candidates/`.
- Newly generated cards should be copied into a new folder, e.g. `final_generated_cards/`.
- Track counts from each `TARGET.txt` to make sure perk quantities are satisfied.

## Current task count hypothesis
- T01 money-token conditional +1 cards: 3 cards
- T02 icon variant A +1 cards: 2 cards
- T03 icon variant B self-effect +1 cards: 2 cards

Validate these against final icon interpretation before final atlas assembly.
