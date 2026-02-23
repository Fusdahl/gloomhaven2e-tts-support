# Class Builder Usage

Builder script:
- `src/build_class_content.py`

Profiles:
- `data/class_profiles.json`

## Build Single-Class Test Objects
Examples:

```bash
python3 src/build_class_content.py single --class-id silent_knife
python3 src/build_class_content.py single --class-id bruiser
```

Default outputs:
- `dist/<OutputPrefix>_saved_object_v2_testable.json`
- `dist/<OutputPrefix>_object_state_v2_testable.json`

Current profile output prefixes:
- `silent_knife` -> `Silent_Knife`
- `bruiser` -> `Bruiser`

## Build Multi-Class Content Pack
Example:

```bash
python3 src/build_class_content.py pack --class-ids silent_knife,bruiser --out-saved dist/GH2E_multi_class_content_pack_saved_object_v1.json
```

This pack command reads the single-class outputs from `dist/` and merges their class boxes into one Classes bag.

## Add Another Class
1. Add a class entry in `data/class_profiles.json`.
2. Provide at minimum:
   - class id/name/hp
   - `ability_order_file`
   - ability atlas face/back paths
   - sheet front/back paths
   - character mat path
   - model source folder under `assets/final_class_models/`
3. Run `single` for that class.
4. Include the class ID in `pack --class-ids ...`.

