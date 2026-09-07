# Public training schema

Schema version `0.2.0` names each run with a short descriptive `title`. The folder is its lowercase hyphenated form, for example `runs/golden-gate-bridge-weather-world/`. Never use random suffixes or opaque identifiers to resolve a collision; choose a more descriptive title and review it.

```text
runs/golden-gate-bridge-weather-world/
├── trace.json
├── metadata.json
└── artifacts/
```

`trace.json` contains only `schema_version`, `title`, `messages`, `steps`, `final_response`, and `limitations`. Messages contain `role` (`user` or `assistant`) and `content`. Chronological steps use sequential integer `index` values; a result may use `call_step` to point to its call's position. These positions express ordering, not source-system identity. Steps can contain `type`, `name`, `input`, `output`, `description`, `status`, `message_index`, and explicit omission/truncation notices.

`metadata.json` contains only `schema_version`, `title`, `source` (platform only), `task` (prompt and task type), `agent` (host and model), `summary` (message/step counts), `artifacts` (relative path, MIME type, byte size, role, privacy review status), `redaction`, and `outcome`. No contributor/account details, timestamps identifying a session, personal paths, run/thread/call IDs, source commits, or integrity digests belong in these records.

The public manifest lists each artifact exactly once under `artifacts/`. Symlinks, credential paths, unlisted files, suspicious filenames, and size mismatches are rejected. Build stores hashes and known private terms in a sibling `.integrity.json` file outside the run; it never uploads that file. Local review and upload use a private digest binding the target and every public byte. Downloaded bundles without the private sidecar can be checked structurally; verify their Git/LFS content hashes against the Hub for transport integrity.

Automated privacy checks supplement mandatory semantic review. Preserve useful design requests, geometry, material, lighting, interaction, implementation, error and validation information. Identify omissions honestly. Do not include raw host logs or dumps with unreviewed fields. Document source licenses and public geographic facts in plain language without identifying the contributor or the source session.
