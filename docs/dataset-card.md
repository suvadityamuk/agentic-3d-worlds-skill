---
pretty_name: Agentic 3D Worlds
language:
- en
tags:
- 3d
- blender
- bpy
- agent-trajectories
configs:
- config_name: default
  data_files:
  - split: train
    path: '**/viewer.parquet'
---

# Agentic 3D Worlds

Agent traces of 3D objects modeled primarily in **Blender with bpy**, paired with their creation code, `.blend` scenes, self-contained GLB exports and rendered previews. Intended for training on Blender modeling workflows.

**Share 3D World Agent Run** collects, redacts and validates these files, then submits a PR after user confirmation. No contributor terminal commands or dataset setup are needed. Three.js-only projects and converted non-Blender runs are excluded.

Runs use short descriptive titles and omit personal data and source identifiers. Capture limitations and artifact licenses accompany each contribution.

The viewer shows rendered previews and GLB file paths. Native mesh tables are included separately; interactive Mesh rendering is currently unsupported by the hosted viewer.

No qualifying Blender examples have been accepted yet.
