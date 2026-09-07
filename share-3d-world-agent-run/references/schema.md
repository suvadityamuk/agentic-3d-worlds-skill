# Public training schema

Schema version `0.3.0` names each run with a short descriptive `title`. The folder is its lowercase hyphenated form, for example `runs/sculpted-ceramic-teapot/`. Never use random suffixes or opaque identifiers to resolve a collision; choose a more descriptive title and review it.

```text
runs/sculpted-ceramic-teapot/
├── trace.json
├── metadata.json
├── viewer.parquet
├── mesh.parquet
└── artifacts/  # create.py, scene.blend, model.glb, preview.png
```

`trace.json` contains only `schema_version`, `title`, `messages`, `steps`, `final_response`, and `limitations`. Messages contain `role` (`user` or `assistant`) and `content`. Chronological steps use sequential integer `index` values; a result may use `call_step` to point to its call's position. These positions express ordering, not source-system identity. Steps can contain `type`, `name`, `input`, `output`, `description`, `status`, `message_index`, and explicit omission/truncation notices.

`metadata.json` contains only `schema_version`, `title`, `source` (platform only), `task` (prompt and task type), `agent` (host and model), `summary` (message/step counts), `artifacts` (relative path, MIME type, byte size, role, privacy review status), `redaction`, and `outcome`. No contributor/account details, timestamps identifying a session, personal paths, run/thread/call IDs, source commits, or integrity digests belong in these records.

The public manifest lists each artifact exactly once under `artifacts/`. Symlinks, credential paths, unlisted files, suspicious filenames, and size mismatches are rejected. Build stores hashes and known private terms in a sibling `.integrity.json` file outside the run; it never uploads that file. Local review and upload use a private digest binding the target and every public byte. Downloaded bundles without the private sidecar can be checked structurally; verify their Git/LFS content hashes against the Hub for transport integrity.

Automated privacy checks supplement mandatory semantic review. Preserve useful design requests, geometry, material, lighting, interaction, implementation, error and validation information. Identify omissions honestly. Do not include raw host logs or dumps with unreviewed fields. Document source licenses and public geographic facts in plain language without identifying the contributor or the source session.

Schema 0.3.0 requires Blender/bpy provenance, real Blender-openable `artifacts/scene.blend`, modeling code `artifacts/create.py`, a self-contained `artifacts/model.glb` and rendered `artifacts/preview.png`. It rejects web projects and archives. `viewer.parquet` has exactly one compatible row: title, repository-relative GLB path, native Image with embedded PNG, and the exact trace/metadata JSON strings. `mesh.parquet` has the same content except the GLB path column is replaced by a native Mesh column with embedded GLB bytes. Both carry Hugging Face feature metadata and must match the reviewed artifact copies. The whole tables participate in private integrity and approval checks. The current hosted viewer does not support Mesh, so the owner config selects only `**/viewer.parquet`; see the Blender reference for the limitation and future activation.
