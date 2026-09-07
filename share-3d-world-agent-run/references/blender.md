# Blender creation and viewer contract

Eligibility is about the original modeling process, not a file extension. Read `create.py` and the actual trace to establish that bpy created or substantially modeled the object. A script that only imports an existing Three.js model and exports it is ineligible. Preserve genuine public execution results and errors. Do not manufacture a run when no qualifying trace exists.

## Required deliverables

At the root of `artifacts/`, use `create.py` (the actual task's bpy modeling code), `scene.blend`, `model.glb`, and `preview.png`. Select supporting Blender assets or documentation explicitly. No JavaScript, TypeScript, HTML, web dependencies or archives are accepted. Do not include helper validation fixtures as examples.

In a sanitized working copy, make linked data local, pack textures, remove personal custom properties, private file paths, unused text blocks and identifying object/material names. Inspect embedded text, image metadata and visible text in the scene. Do not byte-edit Blender files. Save the final scene uncompressed with `bpy.ops.wm.save_as_mainfile(filepath=..., compress=False)`. Retain the actual creation script separately.

Export the same visible mesh geometry through `bpy.ops.export_scene.gltf(filepath=..., export_format='GLB', use_visible=True, export_apply=True, export_extras=False)`. Use mesh objects for final exported surfaces (convert curves/instances in the sanitized final copy if needed), bake procedural materials to portable textures when necessary, and embed resources. Avoid required decoder extensions. GLB is an interactive mesh export, not a raster render: also render the scene camera to `preview.png` using `bpy.ops.render.render(write_still=True)`.

Open the GLB in a 3D viewer, orbit it and compare it with the Blender scene and PNG. Check materials, texture appearance, scale, orientation, framing and missing parts. Record export limitations honestly (e.g. Blender-only shaders, simulations and lighting may differ). Repair before contribution if the GLB is blank or unusable. The helper reopens the blend with auto-execution disabled, imports the GLB, and compares visible mesh triangle counts and world bounds. These checks supplement visual review; they do not establish provenance by themselves.

If Blender is unavailable, retain the run and report that validation cannot complete. The agent may use `BLENDER_EXECUTABLE` to locate an existing installation. Never silently skip the check or ask the contributor to run terminal commands.

## Hugging Face viewer

The helper generates `viewer.parquet` with title, a rendered Image preview, the repository-relative GLB file path, and exact sanitized trace/metadata JSON. It also generates `mesh.parquet` with the native Mesh feature and embedded GLB bytes. Both use descriptive names and contain no absolute local paths, private URLs or expiring links. The tables are checked against the artifacts and included in the same PR and approval digest.

As checked in September 2026, the hosted dataset viewer rejects the Mesh feature (`Feature type 'Mesh' not found`), even though the datasets library supports it. The owner card therefore loads only `**/viewer.parquet`. This shows the rendered image and GLB path without breaking the default viewer. The separately downloadable GLB is self-contained; `mesh.parquet` preserves the native format for a future supported viewer. Do not advertise the PNG as an interactive GLB renderer.

A root zero-row `viewer.parquet` establishes the compatible schema while there are no eligible examples; it is not a synthetic run. Other JSON and native Mesh files are excluded from automatic training-row selection. After merge, inspect the Hub viewer or `/first-rows` endpoint. Report processing failures honestly. Only switch the owner configuration to `**/mesh.parquet` after the hosted service actually recognizes and renders Mesh; do not silently make that global change during a contribution.

References: [Hugging Face Mesh feature](https://github.com/huggingface/datasets/blob/main/docs/source/about_dataset_features.mdx#mesh-feature), [dataset card data configuration](https://huggingface.co/docs/hub/datasets-data-files-configuration).
