#!/usr/bin/env python3
"""Package maintained sources; exclude caches, runtime data, and old archives."""
import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def files(path):
    return sorted(p for p in path.rglob("*") if p.is_file() and
                  not any(part in {"__pycache__", ".DS_Store", ".git", ".share-3d-world-agent-run-runtime"} for part in p.parts) and p.suffix != ".pyc")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    out = parser.parse_args().output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    skill_files = files(ROOT / "share-3d-world-agent-run")
    repo_files = skill_files + [ROOT / "README.md", ROOT / "LICENSE", ROOT / ".gitignore"]
    for folder in ("docs", "examples", "tests", "scripts"):
        repo_files += files(ROOT / folder)
    for name, entries, prefix in (
        ("share-3d-world-agent-run.skill", skill_files, ""),
        ("share-3d-world-agent-run.zip", skill_files, ""),
        ("share-3d-world-agent-run-repo.zip", repo_files, "share-3d-world-agent-run-repo/"),
    ):
        destination = out / name
        with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
            for path in sorted(entries):
                archive.write(path, prefix + path.relative_to(ROOT).as_posix())
        with ZipFile(destination) as archive:
            if archive.testzip() is not None:
                raise RuntimeError(f"Corrupt archive: {destination}")
        print(destination)


if __name__ == "__main__":
    main()
