# Share 3D World Agent Run

Share a Blender/bpy modeling session with its creation code, saved `.blend` scene, self-contained GLB and rendered preview. Invoke the skill during or after a task, review the prepared contribution, and confirm. The agent automatically opens a pull request against the project's public Hugging Face dataset.

Contributors never need to run terminal commands. The dataset is created once by its owner; you only need an agent environment with existing Hugging Face authentication.

## Install

Download and extract this repository or its release archive. Ask your coding agent to install the `share-3d-world-agent-run` folder in its supported skills location, or copy it there using your file manager. Copy the whole folder, including `config.json`, `scripts`, and `references`.

For hosts that discover `.agents/skills`, place the folder at `.agents/skills/share-3d-world-agent-run` inside your project. For another host, use its documented skill directory or skill-import UI. The release includes `share-3d-world-agent-run.skill` (a ZIP-format skill archive) and `share-3d-world-agent-run.zip`; import an archive only if your host supports that format.

The agent needs local file access, Blender, Python 3.10 or newer, permission to execute its helper, and network access to Hugging Face. The helper reuses an available Hub client or prepares an isolated local runtime automatically. Existing HF credentials must be available to the agent; a browser session alone may not provide them. No contributor package-installation or dataset-setup steps are required.

## Use

Say, for example:

> Use Share 3D World Agent Run while you model this object in Blender using bpy, then prepare the finished run for contribution.

Or after a task:

> Use Share 3D World Agent Run to capture this completed task and its artifacts.

The agent collects available messages and tool activity, selects the actual deliverables, redacts and validates a local bundle, and shows what will become public. Confirm the prepared contribution. The agent submits it with a custom description of the task, included artifacts, checks and capture limits, then returns the Hugging Face PR link. If the host cannot expose part of the run, the agent states that limitation.

## Blender requirement

Only runs primarily modeled in Blender through `bpy` qualify. Three.js-only projects and models merely converted into Blender are rejected. Every contribution contains the actual bpy creation script, a saved Blender scene, its validated GLB export and a PNG render. The agent checks the exported geometry and visually reviews the result. Browser project files are excluded.

Each run includes a viewer table with a rendered image, GLB file path and trace, plus a native Mesh table with embedded GLB bytes. The hosted viewer currently rejects the Mesh feature, so its default table uses the compatible image preview. The native table is retained for future support; GLB files are also available separately. Contributors do not prepare this format themselves.

## Destination and contents

[share-3d-world-agent-run/config.json](share-3d-world-agent-run/config.json) is the single source of truth for the target dataset. It defaults to the owner's `suvadityamuk/agentic-3d-worlds`. Contributors use that destination automatically; there are no per-run repository flags or environment-variable overrides.

Each run is named with a short descriptive title. The title also names its PR. Public records exclude contributor details, source-session IDs, personal paths, private links and checksum inventories. Private integrity checks stay on the contributor’s machine.

Each PR contributes only:

```text
runs/sculpted-ceramic-teapot/
├── trace.json
├── metadata.json
├── viewer.parquet
├── mesh.parquet
└── artifacts/  # create.py, scene.blend, model.glb, preview.png
```

Included: relevant visible user/assistant messages, observable tool calls and results, relevant file operations, and selected artifacts. Excluded: hidden reasoning, system/developer instructions, credentials, and unrelated private files. Text redaction is a backstop; the agent also inspects attachments, binaries, and archives before review. Originals remain unchanged.

Uploads always propose changes through a PR, including when the owner uses the skill. The helper never creates repositories, changes visibility, or merges contributions. Its upload behavior uses the official [Hugging Face Hub PR API](https://huggingface.co/docs/huggingface_hub/en/guides/community).

## Maintainer references

These are separate from contributor installation and use:

- [Optional owner-only dataset preparation](docs/owner-setup.md)
- [Development validation and packaging](docs/development.md)
- [Blender acceptance criteria](examples/blender-run/README.md)

## License

MIT. The software license does not automatically license contributed artifacts; contributors must have permission to share the selected material publicly.

The cleaned dialogue, observable steps and artifact sources are intended for later curation and training on 3D worlds and interfaces. Missing context and privacy edits are explicitly documented. The skill does not claim to remove the account and Git/PR metadata that Hugging Face itself displays.
