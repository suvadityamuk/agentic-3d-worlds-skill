# Maintainer development checks

These commands are for maintainers validating changes, not steps for contributors.

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package.py
```

The offline tests exercise capture/redaction, manifest validation, exact-content approval, public target/authentication failures, PR-only upload, and duplicate-attempt handling with a simulated Hub API. They do not create a dataset or a real PR. The package command creates the standalone `.skill`, skill ZIP, and full repository ZIP under `dist/`, excluding caches, local runtime data, and previous archives. Run the host's skill/frontmatter validator against `share-3d-world-agent-run` when available.

For a live integration check, invoke the skill against an actual run, review its concrete bundle, confirm publication, and verify the returned PR in the configured public dataset. This must not be represented as passed based only on offline mocks.
