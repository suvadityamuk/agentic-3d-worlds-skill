# Run bundle schema

## Directory

```text
runs/<run_id>/
├── trace.json
├── metadata.json
└── artifacts/
    └── <deliverables>
```

## trace.json

```json
{
  "schema_version": "0.1.0",
  "run_id": "uuid",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "steps": [
    {
      "index": 1,
      "type": "tool_call",
      "name": "web_search",
      "input": {},
      "output": {},
      "timestamp": null
    }
  ],
  "final_response": "..."
}
```

Required fields: `schema_version`, `run_id`, `messages`, `steps`.

The `steps` objects intentionally allow additional fields. Keep the stable core small so different agents/editors can contribute without bespoke adapters.

Recommended `type` values:
- `message`
- `tool_call`
- `tool_result`
- `web_search`
- `web_fetch`
- `command`
- `file_read`
- `file_write`
- `artifact_created`
- `error`
- `other`

## metadata.json

```json
{
  "schema_version": "0.1.0",
  "run_id": "uuid",
  "created_at": "ISO-8601",
  "source": {"url": null, "platform": null},
  "task": {"prompt": "...", "task_type": "other"},
  "agent": {"host": null, "model": null},
  "summary": {"message_count": 0, "step_count": 0},
  "artifacts": [
    {
      "path": "artifacts/example.ext",
      "mime_type": "application/octet-stream",
      "size_bytes": 0,
      "sha256": "...",
      "role": "final"
    }
  ],
  "redaction": {"performed": true, "matches_redacted": 0},
  "outcome": {"status": "success"}
}
```

## Validation and review additions

Run IDs are canonical UUID strings. `messages` contains only visible `user` and `assistant` entries with `content`; exposed tool activity belongs in `steps`. Add a `limitations` field to the trace and use outcome `partial` for missing context or artifacts.

The manifest lists every included artifact exactly once. Paths must remain under `artifacts/`; symlinks, credential paths, unlisted files, size mismatches, and hash mismatches are rejected. SHA-256 and sizes describe the redacted copies, not the original inputs. Summary counts must match the trace.

Each newly built artifact also includes `privacy_review`: `text_scanned` or `manual_review_required`. This records the automated scan's scope, not a guarantee that a file is safe. Agents must inspect binaries/archives and review the contribution before asking for confirmation.

The review's `approval_digest` binds the configured target and every bundle file's bytes. It is passed to upload after user confirmation and is not stored inside the dataset. Upload receipts live beside the local run directory and are also excluded from contributions. The repository ID comes only from the skill's `config.json`.
