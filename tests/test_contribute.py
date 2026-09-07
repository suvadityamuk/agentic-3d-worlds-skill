"""Offline behavioral checks; never create a real Hub PR."""
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("contribute", ROOT / "share-3d-world-agent-run/scripts/contribute.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class ContributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"repo_id": "owner/public-traces"}))
        self.addCleanup(patch.stopall)
        patch.object(c, "CONFIG_PATH", self.config).start()
        # These tests isolate privacy/approval/Hub behavior. Real Blender gates are
        # covered separately by test_blender_bundle and the local integration fixture.
        patch.object(c, "validate_blender").start()
        self.required = self.root / "blender"
        self.required.mkdir()
        for name in ["scene.blend", "create.py", "model.glb", "preview.png"]:
            (self.required/name).write_bytes(b"fixture")
        self.api = Mock()
        self.api.whoami.return_value = {"name": "contributor"}
        self.api.repo_info.return_value = types.SimpleNamespace(private=False)
        self.api.file_exists.return_value = False
        self.api.upload_folder.return_value = types.SimpleNamespace(pr_url="https://huggingface.co/datasets/owner/public-traces/discussions/12")
        patch.dict("sys.modules", {"huggingface_hub": types.SimpleNamespace(HfApi=Mock(return_value=self.api))}).start()
        self.transcript = self.root / "input.json"
        self.transcript.write_text(json.dumps({"messages": [{"role": "user", "content": "Build a demo"}], "steps": [{"type": "tool_call", "input": {"token": "short-secret"}}]}))
        self.artifact = self.root / "demo.txt"
        self.artifact.write_text("Useful result. hf_" + "A" * 30)

    def execute(self, *args):
        parsed = c.parser().parse_args(args)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            parsed.func(parsed)
        return json.loads(out.getvalue())

    def build(self, *extra):
        self.build_count = getattr(self, "build_count", 0) + 1
        return Path(self.execute("build", "--title", "Demo world take " + str(self.build_count), "--transcript", str(self.transcript), "--artifact", str(self.artifact), "--output", str(self.root / "runs"), *[v for p in self.required.iterdir() for v in ["--artifact",str(p)]], *extra)["run_dir"])

    def reviewed(self):
        run = self.build()
        return run, self.execute("review", "--run-dir", str(run))["approval_digest"]

    def upload(self, run, digest):
        return self.execute("upload", "--run-dir", str(run), "--approved-digest", digest)

    def test_redaction_originals_manifest_and_review(self):
        run = self.build()
        self.assertIn("hf_", self.artifact.read_text())
        self.assertNotIn("hf_", (run / "artifacts/demo.txt").read_text())
        trace = json.loads((run / "trace.json").read_text())
        self.assertEqual(trace["steps"][0]["input"]["token"], "[REDACTED]")
        result = self.execute("review", "--run-dir", str(run))
        self.assertEqual(result["repo_id"], "owner/public-traces")
        self.assertEqual(result["metadata"]["redaction"]["matches_redacted"], 2)
        self.api.upload_folder.assert_not_called()

    def test_upload_is_pr_of_exact_snapshot_and_repeat_is_idempotent(self):
        run, digest = self.reviewed()
        def upload(**kwargs):
            snap = Path(kwargs["folder_path"])
            self.assertNotEqual(snap, run)
            self.assertEqual(c.bundle_digest(snap, "owner/public-traces"), digest)
            self.assertTrue(kwargs["create_pr"])
            self.assertEqual(kwargs["repo_type"], "dataset")
            self.assertEqual(kwargs["path_in_repo"], "runs/" + run.name)
            return types.SimpleNamespace(pr_url="https://huggingface.co/datasets/owner/public-traces/discussions/12")
        self.api.upload_folder.side_effect = upload
        result = self.upload(run, digest)
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(self.upload(run, digest)["pr_url"], result["pr_url"])
        self.api.upload_folder.assert_called_once()
        self.api.create_repo.assert_not_called()
        self.api.upload_file.assert_not_called()

    def test_missing_approval_argument(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            c.parser().parse_args(["upload", "--run-dir", "run"])

    def test_target_change_invalidates_approval(self):
        run, digest = self.reviewed()
        self.config.write_text(json.dumps({"repo_id": "other/dataset"}))
        with self.assertRaisesRegex(ValueError, "differs|integrity"):
            self.upload(run, digest)
        self.api.upload_folder.assert_not_called()

    def test_trace_change_invalidates_approval(self):
        run, digest = self.reviewed()
        trace = run / "trace.json"
        trace.write_text(trace.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "differs|integrity"):
            self.upload(run, digest)

    def test_extra_file_and_tampered_artifact_rejected(self):
        run = self.build()
        extra = run / "unreviewed.txt"
        extra.write_text("private notes")
        with self.assertRaisesRegex(ValueError, "outside"):
            c.validate_run(run)
        extra.unlink()
        (run / "artifacts/demo.txt").write_text("edited")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            c.validate_run(run)

    def test_missing_and_private_target_never_created(self):
        run = self.build()
        self.api.repo_info.side_effect = RuntimeError("not found")
        with self.assertRaisesRegex(RuntimeError, "owner"):
            self.execute("review", "--run-dir", str(run))
        self.api.repo_info.side_effect = None
        self.api.repo_info.return_value.private = True
        with self.assertRaisesRegex(RuntimeError, "private"):
            self.execute("review", "--run-dir", str(run))
        self.api.create_repo.assert_not_called()
        self.api.upload_folder.assert_not_called()

    def test_auth_error_is_safe_and_command_free(self):
        run = self.build()
        self.api.whoami.side_effect = RuntimeError("hf_" + "Z" * 30)
        with self.assertRaisesRegex(RuntimeError, "secure sign-in") as caught:
            self.execute("review", "--run-dir", str(run))
        self.assertNotIn("hf_", str(caught.exception))
        self.assertNotIn("login`", str(caught.exception))

    def test_upload_failure_blocks_blind_retry(self):
        run, digest = self.reviewed()
        self.api.upload_folder.side_effect = TimeoutError("unknown outcome")
        with self.assertRaisesRegex(RuntimeError, "inspect target PRs"):
            self.upload(run, digest)
        with self.assertRaisesRegex(RuntimeError, "earlier submission"):
            self.upload(run, digest)
        self.api.upload_folder.assert_called_once()

    def test_missing_pr_url_not_reported_as_success(self):
        run, digest = self.reviewed()
        self.api.upload_folder.return_value = types.SimpleNamespace(pr_url=None)
        with self.assertRaisesRegex(RuntimeError, "no PR URL"):
            self.upload(run, digest)

    def test_existing_run_not_overwritten(self):
        run, digest = self.reviewed()
        self.api.file_exists.return_value = True
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            self.upload(run, digest)
        self.api.upload_folder.assert_not_called()

    def test_path_traversal_and_symlink_rejected(self):
        with self.assertRaises(ValueError):
            self.build("--title", "../escape")
        self.artifact.unlink()
        self.artifact.symlink_to(self.transcript)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.build()

    def test_directory_credentials_and_name_collision_rejected(self):
        folder = self.root / "product"
        folder.mkdir()
        (folder / ".env").write_text("secret")
        with self.assertRaisesRegex(ValueError, "Credential"):
            self.build("--artifact", str(folder))
        with self.assertRaisesRegex(ValueError, "collide"):
            self.build("--artifact", str(self.artifact))

    def test_binary_preserved_and_flagged_for_review(self):
        self.artifact.write_bytes(b"\x89PNG\x00\xff")
        run = self.build()
        meta = c.validate_run(run)
        self.assertEqual(meta["artifacts"][0]["privacy_review"], "manual_review_required")
        self.assertEqual((run / "artifacts/demo.txt").read_bytes(), self.artifact.read_bytes())

    def test_json_keys_redacted_without_invalid_json(self):
        self.artifact = self.root / "output.json"
        self.artifact.write_text(json.dumps({"password": "short", "result": "fine"}))
        run = self.build()
        data = json.loads((run / "artifacts/output.json").read_text())
        self.assertEqual(data, {"password": "[REDACTED]", "result": "fine"})

    def test_package_lock_dependency_names_preserve_original_bytes(self):
        self.artifact = self.root / "package-lock.json"
        self.artifact.write_text(json.dumps({"packages": {"node_modules/example": {
            "dependencies": {"cookie": "^0.7.1", "token": "^1.0.0"}
        }}}, indent=2))
        run = self.build()
        self.assertEqual((run / "artifacts/package-lock.json").read_bytes(), self.artifact.read_bytes())
        c.validate_run(run)

    def test_package_manifest_still_redacts_actual_secrets(self):
        self.artifact = self.root / "package.json"
        self.artifact.write_text(json.dumps({"dependencies": {"cookie": "^1.0.2"},
                                            "config": {"token": "short-secret"}}))
        run = self.build()
        result = json.loads((run / "artifacts/package.json").read_text())
        self.assertEqual(result["dependencies"]["cookie"], "^1.0.2")
        self.assertEqual(result["config"]["token"], "[REDACTED]")
        c.validate_run(run)

    def test_public_records_use_title_without_source_ids_or_hashes(self):
        self.transcript.write_text(json.dumps({"run_id": "private-run", "source": {"thread_id": "private-thread"},
            "messages": [{"role": "user", "content": "Build a bridge", "source_message_id": "private-message"}],
            "steps": [{"type": "tool_call", "call_id": "private-call", "name": "build"},
                      {"type": "tool_result", "call_id": "private-call", "output": "done"}]}))
        run = self.build()
        trace = json.loads((run / "trace.json").read_text())
        meta = json.loads((run / "metadata.json").read_text())
        self.assertEqual(trace["title"], "Demo world take 1")
        self.assertEqual(run.name, "demo-world-take-1")
        self.assertEqual(trace["steps"][1]["call_step"], 1)
        for value in ["private-run", "private-thread", "private-message", "private-call", "sha256"]:
            self.assertNotIn(value, json.dumps([trace, meta]))
        self.assertTrue(c.private_manifest_path(run).exists())

    def test_private_terms_and_embedded_identifiers_are_removed(self):
        terms = self.root / "private-terms.json"
        terms.write_text(json.dumps(["Alice Example"]))
        self.transcript.write_text(json.dumps({"messages": [{"role": "user", "content":
            "Alice Example: alice@example.com /Users/alice/project 11111111-2222-3333-4444-555555555555"}]}))
        run = self.build("--private-terms-file", str(terms))
        text = (run / "trace.json").read_text()
        for value in ["Alice Example", "alice@example.com", "/Users/alice", "11111111-2222"]:
            self.assertNotIn(value, text)
        self.assertNotIn("private-terms.json", [p.name for p in run.rglob("*")])

    def test_artifact_identity_keys_removed_but_geometry_retained(self):
        self.artifact = self.root / "geometry.json"
        self.artifact.write_text(json.dumps({"id": 123456789, "osmId": 23456789, "name": "Golden Gate Bridge", "points": [[1,2,3]]}))
        run = self.build()
        data = json.loads((run / "artifacts/geometry.json").read_text())
        self.assertEqual(data, {"name": "Golden Gate Bridge", "points": [[1,2,3]]})

    def test_opaque_title_and_same_title_collision_rejected(self):
        with self.assertRaises(ValueError):
            self.build("--title", "11111111-2222-3333-4444-555555555555")
        self.build("--title", "Golden Gate Bridge")
        with self.assertRaises(FileExistsError):
            self.build("--title", "Golden Gate Bridge")

    def test_identifier_filename_rejected(self):
        self.artifact = self.root / "11111111-2222-3333-4444-555555555555.txt"
        self.artifact.write_text("result")
        with self.assertRaisesRegex(ValueError, "filenames"):
            self.build()

    def test_internal_web_and_execution_references_are_removed(self):
        self.transcript.write_text(json.dumps({"messages": [{"role": "user", "content": "Build a bridge"}],
            "steps": [{"type": "tool_result", "output": "turn0search1 way 12345678 cell_id=12"}]}))
        run = self.build()
        text = (run / "trace.json").read_text()
        for value in ["turn0search1", "12345678", "cell_id=12"]:
            self.assertNotIn(value, text)

    def test_system_message_rejected(self):
        self.transcript.write_text(json.dumps({"messages": [{"role": "system", "content": "private instructions"}]}))
        with self.assertRaisesRegex(ValueError, "visible user/assistant"):
            self.build()

    def test_repo_env_override_is_ignored_and_bootstrap_is_absent(self):
        with patch.dict("os.environ", {"HF_DATASET_REPO": "wrong/dataset"}):
            self.assertEqual(c.configured_repo(), "owner/public-traces")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            c.parser().parse_args(["bootstrap"])


if __name__ == "__main__":
    unittest.main()
