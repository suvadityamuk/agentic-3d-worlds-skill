# Agent-operated helper

These instructions are for the agent, not terminal steps for the contributor. Resolve the installed skill directory to an absolute path. Run from a writable task workspace. Use the host's Python 3.10+ executable.

`scripts/run.py` dispatches local build/validation without extra packages. For review/upload it reuses an available `huggingface_hub`, or automatically creates `.share-3d-world-agent-run-runtime` in the working directory and installs the client there. Keep that directory out of captures. Never install into system Python. If host permissions block execution or dependency retrieval, retain the bundle and explain the limitation; do not delegate commands to the contributor.

## Build

Write an input JSON object with `messages` and `steps`, optionally `final_response` and `limitations`. Messages contain only relevant visible user/assistant content. Steps contain the chronological observable activity and may include available inputs, outputs, and timestamps. Use `--status partial` when reconstructing an incomplete run.

Agent command (replace placeholders with actual paths; do not show it as a user task):

```sh
python /absolute/skill/scripts/run.py build --transcript /absolute/transcript.json --artifact /absolute/deliverable --output /absolute/workspace/agent-runs
```

Repeat `--artifact` for selected files/directories. Optional flags include `--source`, `--platform`, `--host`, `--model`, `--task-type`, and `--status`. The output reports the generated run directory. Inspect its redacted copies, including manually reviewing binary/archive artifacts. If you edit a bundle, rebuild to refresh the manifest before review.

## Review, then upload

```sh
python /absolute/skill/scripts/run.py review --run-dir /absolute/workspace/agent-runs/UUID
```

This validates the bundle and returns the public target, existing contributor identity, file manifest, counts, redaction details, and `approval_digest`. Present these in plain language with a link to the bundle. Ask for confirmation of these exact contents and target. Save the returned digest in your task context.

Only after confirmation:

```sh
python /absolute/skill/scripts/run.py upload --run-dir /absolute/workspace/agent-runs/UUID --approved-digest DIGEST_FROM_REVIEW
```

Never treat possessing a digest as user consent. The digest binds the target and bundle bytes; the agent is responsible for obtaining the user's confirmation. The uploader checks it again and returns `pr_url`. Local validation is also available through `validate --run-dir ...`.

Successful submission writes a receipt beside the bundle, not inside it. Repeating an identical successful submission returns the stored PR URL. An uncertain/failed attempt blocks automatic retry: inspect the target's PRs using the Hub interface/API. Reconcile the receipt with a found PR; only after establishing that no PR was created may the agent remove that run's sibling receipt and retry the same approved bundle. If uncertain, keep the bundle and report the pending outcome.
