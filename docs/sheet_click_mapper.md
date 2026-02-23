# Sheet Click Mapper

Use `tools/sheet_click_mapper.html` to capture `perk_positions` and `mastery_positions` from one class sheet image.

## Open the tool

From repo root:

```bash
open tools/sheet_click_mapper.html
```

## Workflow

1. Load class front sheet image from `assets/FH_compatible_sheets`.
2. Click `Set Level 1`, then click the center of level-1 checkbox.
3. Click `Set Level 9`, then click the center of level-9 checkbox.
4. Click `Add Perk`, then click each perk checkbox in order (top-to-bottom, left-to-right on each row).
5. Click `Add Mastery`, then click mastery checkboxes in order.
6. Copy output block and paste into class entry in `data/class_profiles.json`.
7. Rebuild class JSON:

```bash
python3 src/build_class_content.py single --class-id <class_id>
```

## Notes

- Calibration is done from the same image, so no cross-class comparison is required.
- If points are wrong, use `Undo Last` or `Clear All`.
- This tool emits coordinates in the Lua/UI coordinate system used by character sheet scripts.
