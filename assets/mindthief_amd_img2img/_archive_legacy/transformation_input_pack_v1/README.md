# Mindthief AMD Transformation Pack (v1)

## Start
1. If you accept worldhaven cards as-is, use `00_direct_use_target_cards` directly.
2. If you want style harmonization, process folders `01_...` onward one at a time.

## Per-folder workflow
1. Open folder and read `TASK.txt`.
2. Use `BASE_...` plus `target_refs/*` in img2img.
3. Generate one master output for that effect.
4. Duplicate that master to the count in `TASK.txt` when assembling atlas.
