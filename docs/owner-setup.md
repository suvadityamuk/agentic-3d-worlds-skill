# Optional owner-only dataset preparation

This page is for the dataset maintainer. It is not a contributor prerequisite or part of skill installation/use. Skip it when the public dataset already exists.

1. Read the target in `share-3d-world-agent-run/config.json`. This is the only configurable repository ID; change it here if maintaining a fork with a different central dataset.
2. In the Hugging Face website, create a **Dataset** at that exact namespace/name and choose **Public** visibility. Initialize its dataset card/default branch, describe the contribution format and public-sharing terms, and ensure community PRs are enabled.
3. Review incoming PRs and merge accepted contributions using the Hub interface.

No bootstrap helper is needed. Dataset creation and visibility changes are intentionally absent from the contributor script. Do not ask contributors to create their own datasets. Changing the target requires a new contribution review before upload.
