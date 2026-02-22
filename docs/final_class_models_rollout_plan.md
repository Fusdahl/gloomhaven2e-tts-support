# Final Class Models Rollout Plan (GH1-Based)

## Goal
Build `assets/final_class_models` coverage for all GH2E classes by sourcing box/model assets from GH1 saved objects, then wiring each class builder to local GitHub raw URLs.

## Class Mapping (GH2E -> GH1 Source)
1. `silent_knife` -> `Scoundrel`
2. `bruiser` -> `Brute`
3. `cragheart` -> `Cragheart`
4. `mindthief` -> `Mindthief`
5. `spellweaver` -> `Spellweaver`
6. `tinkerer` -> `Tinkerer`
7. `berserker` -> `Berserker`
8. `bladeswarm` -> `Bladeswarm`
9. `doomstalker` -> `Doomstalker`
10. `elementalist` -> `Elementalist`
11. `nightshroud` -> `Nightshroud`
12. `plagueherald` -> `Plagueherald`
13. `quartermaster` -> `Quartermaster`
14. `sawbones` -> `Sawbones`
15. `sunkeeper` -> `Sunkeeper`
16. `soothsinger` -> `Soothsinger`
17. `wildfury` -> `Beast Tyrant`
18. `soultether` -> `Summoner`

## Standard Asset Contract Per Class
Each class folder should provide:
1. `class_top_box_mesh.obj`
2. `class_top_box_diffuse.png`
3. `class_top_box_icon.png`
4. `class_box_mesh.obj`
5. `class_box_diffuse.png`
6. `character_box_mask_front.png`
7. `character_box_mask_side.png`
8. `class_figure.unity3d`
9. `class_icon.png`
10. `manifest.json` (source URLs, SHA256, dimensions, notes)

## Folder Layout
1. `assets/final_class_models/<class_id>/...` for class-specific files
2. Optional shared folder for repeated meshes:
   `assets/final_class_models/_shared/` (`top_box_mesh.obj`, `small_box_mesh.obj`)

## Extraction Workflow (Per Class)
1. Load GH1 source JSON: `saved objects for working 1st class/<Class>  top box.json`.
2. Parse and extract:
   - Top box `CustomMesh` (`MeshURL`, `DiffuseURL`)
   - Small box `CustomMesh` (`MeshURL`, `DiffuseURL`)
   - Figure `CustomAssetbundle.AssetbundleURL`
   - Relevant icon/mask `CustomUIAssets` URLs
3. Download all referenced URLs to class folder.
4. Normalize filenames to contract above.
5. Record metadata in `manifest.json`.

## Validation Gates (Per Class)
1. File presence: all contract files exist.
2. Basic integrity:
   - `*.png` openable
   - `*.obj` non-empty
   - `*.unity3d` non-empty
3. Dimension sanity:
   - top diffuse typically 2048x2048
   - small diffuse typically ~1800 square
4. Hashes logged in `manifest.json`.

## Builder Integration
1. Add per-class model URL constants from `assets/final_class_models/<class_id>/...`.
2. Keep a single `ASSET_REV` token for cache busting.
3. Ensure both outputs regenerate:
   - `dist/<Class>_saved_object_*.json`
   - `dist/<Class>_object_state_*.json`

## TTS Acceptance Criteria (Per Class)
1. Big box visual matches intended class styling.
2. Small box visual matches intended class styling.
3. Figure loads correctly.
4. No fallback/legacy Steam URLs in final dist JSON.
5. Drop flow remains:
   - big box -> small box -> class contents.

## Execution Order
1. Complete one pilot class end-to-end (already: `silent_knife`).
2. Batch remaining classes in sets of 3-4 to keep verification manageable.
3. After each batch:
   - regenerate dist
   - run URL/hierarchy checks
   - smoke test in TTS.
