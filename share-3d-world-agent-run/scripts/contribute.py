#!/usr/bin/env python3
"""Build, validate, and upload simple agent-run bundles."""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import tempfile
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "0.1.0"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"

SECRET_PATTERNS = [
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]{20,}=*"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*['\"]?[^\s,'\"}]{12,}"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def redact_text(text: str) -> tuple[str, int]:
    count = 0
    for pattern in SECRET_PATTERNS:
        text, n = pattern.subn("[REDACTED]", text)
        count += n
    return text, count


def redact_obj(obj: Any) -> tuple[Any, int]:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        pairs = [redact_obj(value) for value in obj]
        return [value for value, _ in pairs], sum(count for _, count in pairs)
    if isinstance(obj, dict):
        result, count = {}, 0
        for key, value in obj.items():
            if re.fullmatch(r"(?i)(?:api[_-]?key|token|access[_-]?token|password|secret|authorization|cookie|set-cookie)", key):
                if value and value != "[REDACTED]":
                    result[key], count = "[REDACTED]", count + 1
                else:
                    result[key] = value
            else:
                result[key], n = redact_obj(value)
                count += n
        return result, count
    return obj, 0


def configured_repo() -> str:
    repo_id = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["repo_id"]
    if not isinstance(repo_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", repo_id):
        raise ValueError("config.json must contain an owner/dataset repo_id")
    return repo_id


def validate_run_id(run_id: str) -> None:
    if str(uuid.UUID(run_id)) != run_id:
        raise ValueError("run_id must be a canonical UUID")


def check_artifact_path(path: Path) -> None:
    blocked = {".git", ".ssh", ".aws", ".cache", ".share-3d-world-agent-run-runtime", "__pycache__", "id_rsa", "id_ed25519", "credentials", ".netrc"}
    for part in path.parts:
        if part.lower() in blocked or part.lower().startswith(".env"):
            raise ValueError("Credential/cache paths cannot be included as artifacts")
    if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
        raise ValueError("Private-key containers cannot be included as artifacts")


def redact_artifact(path: Path) -> tuple[int, str]:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeError:
        return 0, "manual_review_required"
    if "\x00" in content:
        return 0, "manual_review_required"
    redacted, count = redact_text(content)
    if path.suffix.lower() == ".json":
        try:
            obj, extra = redact_obj(json.loads(redacted))
            if extra:
                redacted = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
                count += extra
        except json.JSONDecodeError:
            pass
    if count:
        path.write_text(redacted, encoding="utf-8")
    return count, "text_scanned"


def load_transcript(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"messages": data, "steps": []}
    if not isinstance(data, dict):
        raise ValueError("Transcript must be a JSON object or list of messages")
    data.setdefault("messages", [])
    data.setdefault("steps", [])
    if not isinstance(data["messages"], list) or not isinstance(data["steps"], list):
        raise ValueError("messages and steps must be arrays")
    return data


def infer_prompt(messages: list[dict[str, Any]]) -> str:
    for msg in messages:
        if str(msg.get("role", "")).lower() == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content[:4000]
    return ""


def copy_artifact(src: Path, dst_root: Path) -> list[Path]:
    if src.is_symlink():
        raise ValueError("Artifact symlinks are not allowed")
    if not src.exists():
        raise FileNotFoundError(src)
    entries = [src, *src.rglob("*")] if src.is_dir() else [src]
    for entry in entries:
        check_artifact_path(entry.relative_to(src.parent))
        if entry.is_symlink() or not (entry.is_dir() or entry.is_file()):
            raise ValueError("Artifact symlinks and special files are not allowed")
    dst = dst_root / src.name
    if dst.exists():
        raise ValueError("Selected artifact names collide; rename selected copies first")
    if src.is_dir():
        shutil.copytree(src, dst)
        return sorted(p for p in dst.rglob("*") if p.is_file())
    shutil.copy2(src, dst)
    return [dst]


def build(args: argparse.Namespace) -> int:
    transcript = load_transcript(Path(args.transcript))
    run_id = args.run_id or str(uuid.uuid4())
    validate_run_id(run_id)
    out_base = Path(args.output).expanduser().resolve()
    run_dir = out_base / run_id
    artifact_root = run_dir / "artifacts"
    artifact_root.mkdir(parents=True, exist_ok=False)

    transcript["schema_version"] = SCHEMA_VERSION
    transcript["run_id"] = run_id
    redacted_transcript, redaction_count = redact_obj(transcript)

    artifacts_meta = []
    for artifact in args.artifact or []:
        copied = copy_artifact(Path(artifact).expanduser().absolute(), artifact_root)
        for p in copied:
            count, scan = redact_artifact(p)
            redaction_count += count
            rel = p.relative_to(run_dir).as_posix()
            mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            artifacts_meta.append({
                "path": rel,
                "mime_type": mime,
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
                "role": "final",
                "privacy_review": scan,
            })

    messages = redacted_transcript.get("messages", [])
    steps = redacted_transcript.get("steps", [])
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": now_iso(),
        "source": {"url": args.source, "platform": args.platform},
        "task": {"prompt": args.prompt or infer_prompt(messages), "task_type": args.task_type},
        "agent": {"host": args.host, "model": args.model},
        "summary": {"message_count": len(messages), "step_count": len(steps)},
        "artifacts": artifacts_meta,
        "redaction": {"performed": True, "matches_redacted": redaction_count},
        "outcome": {"status": args.status},
    }
    metadata, meta_redactions = redact_obj(metadata)
    metadata["redaction"]["matches_redacted"] += meta_redactions

    with (run_dir / "trace.json").open("w", encoding="utf-8") as f:
        json.dump(redacted_transcript, f, indent=2, ensure_ascii=False)
        f.write("\n")
    with (run_dir / "metadata.json").open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        f.write("\n")

    validate_run(run_dir)
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "metadata": metadata}, indent=2))
    return 0


def validate_run(run_dir: Path) -> dict[str, Any]:
    validate_run_id(run_dir.name)
    if run_dir.is_symlink():
        raise ValueError("Run directory cannot be a symlink")
    paths = list(run_dir.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths):
        raise ValueError("Run contains symlinks or special files")
    if not (run_dir / "artifacts").is_dir():
        raise ValueError("Missing artifacts directory")
    trace = json.loads((run_dir / "trace.json").read_text(encoding="utf-8"))
    meta = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    if trace.get("schema_version") != SCHEMA_VERSION or meta.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported schema_version")
    if trace.get("run_id") != meta.get("run_id") or trace.get("run_id") != run_dir.name:
        raise ValueError("run_id mismatch")
    if not isinstance(trace.get("messages"), list) or not isinstance(trace.get("steps"), list):
        raise ValueError("trace messages/steps must be arrays")
    if any(not isinstance(m, dict) or m.get("role") not in {"user", "assistant"} or "content" not in m for m in trace["messages"]):
        raise ValueError("Messages must contain visible user/assistant content; put exposed tool activity in steps")
    if any(not isinstance(step, dict) for step in trace["steps"]):
        raise ValueError("Steps must be objects")
    if meta.get("summary") != {"message_count": len(trace["messages"]), "step_count": len(trace["steps"])}:
        raise ValueError("Summary counts do not match trace")
    if meta.get("outcome", {}).get("status") not in {"success", "partial", "failed"}:
        raise ValueError("Invalid outcome")
    if meta.get("redaction", {}).get("performed") is not True:
        raise ValueError("Redaction is required")
    for obj in (trace, meta):
        if redact_obj(obj)[1]:
            raise ValueError("Unredacted credential pattern in trace/metadata; rebuild before review")
    if not isinstance(meta.get("artifacts"), list):
        raise ValueError("Artifact manifest must be an array")
    expected = {"trace.json", "metadata.json"}
    for artifact in meta["artifacts"]:
        rel = artifact["path"]
        path = Path(rel)
        if path.is_absolute() or ".." in path.parts or len(path.parts) < 2 or path.parts[0] != "artifacts" or path.as_posix() != rel:
            raise ValueError("Invalid artifact path")
        check_artifact_path(path)
        if rel in expected:
            raise ValueError("Duplicate artifact path")
        expected.add(rel)
        p = run_dir / rel
        if not p.is_file() or p.stat().st_size != artifact["size_bytes"] or sha256_file(p) != artifact["sha256"]:
            raise ValueError("Artifact missing or hash/size mismatch")
        try:
            content = p.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if "\x00" not in content:
            if redact_text(content)[1]:
                raise ValueError("Unredacted credential pattern in text artifact")
            if p.suffix.lower() == ".json":
                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError:
                    continue
                if redact_obj(parsed)[1]:
                    raise ValueError("Unredacted secret key in JSON artifact")
    actual = {p.relative_to(run_dir).as_posix() for p in paths if p.is_file()}
    if actual != expected:
        raise ValueError("Run contains files outside the validated manifest")
    return meta


def bundle_digest(run_dir: Path, repo_id: str) -> str:
    files = {p.relative_to(run_dir).as_posix(): sha256_file(p)
             for p in sorted(run_dir.rglob("*")) if p.is_file()}
    data = json.dumps({"repo_id": repo_id, "files": files}, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


def hub_context(repo_id: str):
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise RuntimeError("Agent runtime is unavailable; use the bundled agent runner") from None
    api = HfApi(token=os.environ.get("HF_TOKEN") or None)
    try:
        who = api.whoami()
    except Exception:
        raise RuntimeError("Hugging Face authentication is unavailable. Reconnect through the host's secure sign-in interface; never paste a token into chat.") from None
    try:
        info = api.repo_info(repo_id=repo_id, repo_type="dataset")
    except Exception:
        raise RuntimeError("Configured dataset is missing or inaccessible. The owner must make the existing target available; the bundle is retained.") from None
    if info.private:
        raise RuntimeError("Configured dataset is private; the owner must provide the public target")
    return api, who


def review(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().absolute()
    meta = validate_run(run_dir)
    repo_id = configured_repo()
    _, who = hub_context(repo_id)
    print(json.dumps({"repo_id": repo_id, "public": True,
        "contributor": who.get("name"), "run_dir": str(run_dir),
        "approval_digest": bundle_digest(run_dir, repo_id),
        "total_bytes": sum(p.stat().st_size for p in run_dir.rglob("*") if p.is_file()),
        "metadata": meta}, indent=2))
    return 0


def validate(args: argparse.Namespace) -> int:
    meta = validate_run(Path(args.run_dir).expanduser().resolve())
    print(json.dumps({"valid": True, "run_id": meta["run_id"]}, indent=2))
    return 0


def upload(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().absolute()
    meta = validate_run(run_dir)
    repo_id = configured_repo()
    digest = bundle_digest(run_dir, repo_id)
    if args.approved_digest != digest:
        raise ValueError("Bundle or target differs from the approved review; review and confirm again")
    receipt_path = run_dir.parent / f".{meta['run_id']}.submission.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("approval_digest") == digest and receipt.get("pr_url"):
            print(json.dumps(receipt, indent=2))
            return 0
        raise RuntimeError("An earlier submission may have created a PR. Inspect the target's PRs and reconcile the local receipt before retrying")
    api, who = hub_context(repo_id)
    remote_path = f"runs/{meta['run_id']}"
    try:
        exists = api.file_exists(repo_id=repo_id, filename=f"{remote_path}/metadata.json", repo_type="dataset")
    except Exception:
        raise RuntimeError("Could not check for an existing run; bundle retained") from None
    if exists:
        raise RuntimeError("This run already exists in the dataset; refusing to replace it")
    # Upload a validated snapshot so later edits to the working bundle cannot enter the PR.
    with tempfile.TemporaryDirectory(prefix="share-3d-world-agent-run-upload-") as tmp:
        snapshot = Path(tmp) / meta["run_id"]
        shutil.copytree(run_dir, snapshot)
        validate_run(snapshot)
        if bundle_digest(snapshot, repo_id) != digest:
            raise ValueError("Bundle changed during preparation; review and confirm again")
        receipt = {"repo_id": repo_id, "run_id": meta["run_id"],
                   "contributor": who.get("name"), "approval_digest": digest, "status": "pending"}
        with receipt_path.open("x", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        try:
            result = api.upload_folder(
                folder_path=str(snapshot), path_in_repo=remote_path,
                repo_id=repo_id, repo_type="dataset", create_pr=True,
                allow_patterns=["trace.json", "metadata.json", *[a["path"] for a in meta["artifacts"]]],
                commit_message=f"Add agent run {meta['run_id']}",
            )
        except Exception:
            raise RuntimeError("Upload did not return a confirmed PR. Bundle retained; inspect target PRs before retrying to avoid duplicates") from None
        pr_url = getattr(result, "pr_url", None)
        if not pr_url:
            raise RuntimeError("Hub returned no PR URL. Inspect target PRs before retrying; do not assume submission failed")
        receipt.update(status="submitted", pr_url=pr_url)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build and submit agent-run dataset contributions")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Build and validate a run bundle")
    b.add_argument("--transcript", required=True)
    b.add_argument("--artifact", action="append", default=[])
    b.add_argument("--source")
    b.add_argument("--platform")
    b.add_argument("--prompt")
    b.add_argument("--task-type", default="other")
    b.add_argument("--host")
    b.add_argument("--model")
    b.add_argument("--status", default="success", choices=["success", "partial", "failed"])
    b.add_argument("--run-id")
    b.add_argument("--output", default="agent-runs")
    b.set_defaults(func=build)

    v = sub.add_parser("validate", help="Validate an existing run bundle")
    v.add_argument("--run-dir", required=True)
    v.set_defaults(func=validate)

    r = sub.add_parser("review", help="Prepare a validated public contribution for user confirmation")
    r.add_argument("--run-dir", required=True)
    r.set_defaults(func=review)

    u = sub.add_parser("upload", help="Upload a run to a Hugging Face Dataset as a PR")
    u.add_argument("--run-dir", required=True)
    u.add_argument("--approved-digest", required=True, help="Digest of the prepared bundle explicitly confirmed by the user")
    u.set_defaults(func=upload)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
