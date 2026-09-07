# Shared Codex acceptance case

Canonical source: https://chatgpt.com/s/cx_6a9eb1869d648191827e8526ac5831da

Ask an agent with the installed skill to capture this visible shared run and its actual artifacts. The agent reads the exposed transcript, retrieves every available final artifact, records the source, builds/redacts/validates the bundle, and presents it for confirmation. After confirmation, it automatically opens a PR against the dataset in `share-3d-world-agent-run/config.json` and verifies the PR contains `trace.json`, `metadata.json`, and all final artifacts.

The contributor runs no commands and does not create a dataset. If source content or final artifacts cannot be retrieved, report the missing items and mark recovery partial; do not invent replacements or claim this acceptance case passed. Local synthetic tests validate helper behavior, not successful recovery of this original shared run.
