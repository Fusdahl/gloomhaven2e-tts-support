# Sheet Positions Store

Use `data/class_sheet_positions.json` as the reusable source of truth for:

- `perk_positions`
- `mastery_positions`

for each class.

## Workflow

1. Capture coordinates with the click tool:
   - `tools/sheet_click_mapper.html`
2. Paste output into the class entry in:
   - `data/class_sheet_positions.json`
3. Sync into class profiles:

```bash
python3 src/sync_sheet_positions.py --class-id <class_id>
```

or sync all completed classes:

```bash
python3 src/sync_sheet_positions.py
```

4. Rebuild class test object:

```bash
python3 src/build_class_content.py single --class-id <class_id>
```

## Notes

- Only entries with non-empty valid arrays are synced.
- If a class exists in `class_sheet_positions.json` but not in `class_profiles.json`, it is reported and skipped.
- `silent_knife` and `bruiser` are pre-seeded.
