"""Check that dependency handling remains agent-operated and isolated."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runner", ROOT / "share-3d-world-agent-run/scripts/run.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class RunnerTests(unittest.TestCase):
    def test_help_does_not_prepare_dependencies(self):
        with patch.object(r.sys, "argv", ["run.py", "build", "--help"]), patch.object(r.venv, "EnvBuilder") as env, patch.object(r.subprocess, "call", return_value=0) as call:
            self.assertEqual(r.main(), 0)
            env.assert_not_called()
            self.assertEqual(call.call_args.args[0][-1], "--help")

    def test_missing_hub_client_prepared_in_local_venv(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(r.Path, "cwd", return_value=Path(tmp)), patch.object(r.sys, "argv", ["run.py", "review", "--run-dir", "bundle"]), patch.object(r.importlib.util, "find_spec", return_value=None), patch.object(r.venv, "EnvBuilder") as env, patch.object(r.subprocess, "run", side_effect=[types.SimpleNamespace(returncode=1), types.SimpleNamespace(returncode=0)]) as run, patch.object(r.subprocess, "call", return_value=0) as call:
            self.assertEqual(r.main(), 0)
            env.return_value.create.assert_called_once_with(Path(tmp) / ".share-3d-world-agent-run-runtime")
            install = run.call_args_list[1].args[0]
            self.assertIn(str(Path(tmp) / ".share-3d-world-agent-run-runtime"), install[0])
            self.assertEqual(install[1:4], ["-m", "pip", "install"])
            self.assertEqual(call.call_args.args[0][0], install[0])

    def test_available_client_reused(self):
        with patch.object(r.sys, "argv", ["run.py", "review"]), patch.object(r.importlib.util, "find_spec", return_value=object()), patch.object(r.venv, "EnvBuilder") as env, patch.object(r.subprocess, "call", return_value=0) as call:
            self.assertEqual(r.main(), 0)
            env.assert_not_called()
            self.assertEqual(call.call_args.args[0][0], r.sys.executable)


if __name__ == "__main__":
    unittest.main()
