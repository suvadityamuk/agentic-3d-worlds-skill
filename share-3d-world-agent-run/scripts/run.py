#!/usr/bin/env python3
"""Agent runner: prepare an isolated Hub runtime only when needed."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import venv


def main() -> int:
    helper = Path(__file__).with_name("contribute.py")
    if sys.version_info < (3, 10):
        print("Agent host needs Python 3.10 or newer; contribution is retained.", file=sys.stderr)
        return 2
    needs_hub = len(sys.argv) > 1 and sys.argv[1] in {"review", "upload"} and "--help" not in sys.argv
    executable = sys.executable
    if needs_hub and importlib.util.find_spec("huggingface_hub") is None:
        runtime = Path.cwd() / ".share-3d-world-agent-run-runtime"
        executable = str(runtime / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
        try:
            if not Path(executable).exists():
                venv.EnvBuilder(with_pip=True).create(runtime)
            probe = subprocess.run([executable, "-c", "import huggingface_hub"], capture_output=True)
            if probe.returncode:
                # Never surface installer output, which can contain private index credentials.
                subprocess.run([executable, "-m", "pip", "install", "huggingface_hub>=0.34,<2"], check=True, capture_output=True)
        except Exception:
            print("Agent could not prepare its isolated Hub runtime. Bundle retained; check host execution/network access.", file=sys.stderr)
            return 2
    return subprocess.call([executable, str(helper), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
