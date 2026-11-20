import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from installed_check import output, qualify
from preview_transition import EXE, exercise, installed_go, transition_order, verify_rpm


class InstallerTests(unittest.TestCase):
    def test_same_version_wrong_bytes_refused_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary, archive = root / "installed", root / "archive"
            binary.write_bytes(b"another executable")
            archive.write_bytes(b"qualified executable")
            with patch("installed_check.output") as launch:
                with self.assertRaisesRegex(ValueError, "differs from the qualified archive"):
                    qualify(binary, "0.0.1-pre.2", expected=archive)
                launch.assert_not_called()

    def test_bounded_process_reports_current_check(self):
        with self.assertRaisesRegex(RuntimeError, "blocked test process.*timed out"):
            output(sys.executable, "-c", "import time; time.sleep(10)", label="blocked test process", timeout=0.1)

    def test_failure_in_update_closes_installer_preserving_original_error(self):
        installer = Mock(channel="fake")
        installer.present.return_value = False
        installer.qualify.side_effect = [None, RuntimeError("update check failed")]
        installer.close.side_effect = RuntimeError("cleanup also failed")
        with self.assertRaisesRegex(RuntimeError, "update check failed"):
            exercise(installer, [("install", SimpleNamespace(version="old")),
                                 ("update", SimpleNamespace(version="new"))])
        installer.close.assert_called_once()

    def test_transition_order(self):
        transition_order("v0.0.1-pre.2", "v0.0.1-pre.10")
        for previous, current in (
            ("", "v0.0.1-pre.2"), ("v0.0.1-pre.2", "v0.0.1"),
            ("v0.0.1-pre.3", "v0.0.1-pre.2"), ("v0.0.1-01", "v0.0.1-pre.2"),
        ):
            with self.assertRaises(ValueError):
                transition_order(previous, current)

    def test_go_install_isolates_default_and_direct_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            default = root / "default"
            default.mkdir()
            sentinel = default / EXE
            sentinel.write_bytes(b"existing")
            bundle = SimpleNamespace(record={"source_tag": "v0.0.1-pre.2"})
            with patch.dict(os.environ, GOBIN=str(default), GOPROXY="example.invalid"), patch(
                "preview_transition.invoke",
            ) as go:
                for route in ("proxy-default", "direct"):
                    binary = installed_go(bundle, None, root / route, route)
                    self.assertEqual(binary, root / route / "bin" / EXE)
                    self.assertEqual(go.call_args.args, (
                        "go", "install", "github.com/valasme/receipts/cmd/receipts@v0.0.1-pre.2",
                    ))
                    env = go.call_args.kwargs["env"]
                    self.assertEqual(env["GOBIN"], str(binary.parent))
                    self.assertEqual(env["GOMODCACHE"], str(root / route / "modcache"))
                    self.assertEqual(env.get("GOPROXY"), "direct" if route == "direct" else None)
            self.assertEqual(sentinel.read_bytes(), b"existing")

    def test_rpm_header_architecture(self):
        for arch, header in (("amd64", "x86_64"), ("arm64", "aarch64")):
            with patch("preview_transition.ARCH", arch), patch("preview_transition.text", return_value=header) as rpm:
                verify_rpm(Path("candidate.rpm"))
                self.assertIn("%{ARCH}", rpm.call_args.args)
                rpm.return_value = "noarch"
                with self.assertRaisesRegex(ValueError, f"expected {header}"):
                    verify_rpm(Path("candidate.rpm"))


if __name__ == "__main__":
    unittest.main()
