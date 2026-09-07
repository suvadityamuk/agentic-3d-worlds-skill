# Share 3D World Agent Run

Share an agent's observable work session together with the files it produced. Invoke the skill during or after a task, review the prepared contribution, and confirm. The agent automatically opens a pull request against the project's public Hugging Face dataset.

Contributors never need to run terminal commands. The dataset is created once by its owner; you only need an agent environment with existing Hugging Face authentication.

## Install

Download and extract this repository or its release archive. Ask your coding agent to install the `share-3d-world-agent-run` folder in its supported skills location, or copy it there using your file manager. Copy the whole folder, including `config.json`, `scripts`, and `references`.

For hosts that discover `.agents/skills`, place the folder at `.agents/skills/share-3d-world-agent-run` inside your project. For another host, use its documented skill directory or skill-import UI. The release includes `share-3d-world-agent-run.skill` (a ZIP-format skill archive) and `share-3d-world-agent-run.zip`; import an archive only if your host supports that format.

The agent needs local file access, Python 3.10 or newer, permission to execute its helper, and network access to Hugging Face. The helper reuses an available Hub client or prepares an isolated local runtime automatically. Existing HF credentials must be available to the agent; a browser session alone may not provide them. No contributor package-installation or dataset-setup steps are required.

## Use

Say, for example:

> Use Share 3D World Agent Run while you build this demo, then prepare the finished run for contribution.

Or after a task:

> Use Share 3D World Agent Run to capture this completed task and its artifacts.

The agent collects available messages and tool activity, selects the actual deliverables, redacts and validates a local bundle, and shows what will become public. Confirm the prepared contribution. The agent submits it and returns the Hugging Face PR link. If the host cannot expose part of the run, the agent states that limitation.

## Destination and contents

[share-3d-world-agent-run/config.json](share-3d-world-agent-run/config.json) is the single source of truth for the target dataset. It defaults to the owner's `suvadityamuk/agentic-3d-worlds`. Contributors use that destination automatically; there are no per-run repository flags or environment-variable overrides.

Each PR contributes only:

```text
runs/<run-id>/
├── trace.json
├── metadata.json
└── artifacts/
```

Included: relevant visible user/assistant messages, observable tool calls and results, relevant file operations, and selected artifacts. Excluded: hidden reasoning, system/developer instructions, credentials, and unrelated private files. Text redaction is a backstop; the agent also inspects attachments, binaries, and archives before review. Originals remain unchanged.

Uploads always propose changes through a PR, including when the owner uses the skill. The helper never creates repositories, changes visibility, or merges contributions. Its upload behavior uses the official [Hugging Face Hub PR API](https://huggingface.co/docs/huggingface_hub/en/guides/community).

## Maintainer references

These are separate from contributor installation and use:

- [Optional owner-only dataset preparation](docs/owner-setup.md)
- [Development validation and packaging](docs/development.md)
- [Original shared-chat acceptance case](examples/shared-codex-test/README.md)

## License

MIT. The software license does not automatically license contributed artifacts; contributors must have permission to share the selected material publicly.
