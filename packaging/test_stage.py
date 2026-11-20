import hashlib
import tempfile
import unittest
from pathlib import Path

from stage import reconcile


class DraftRecovery(unittest.TestCase):
    def test_resume_only_missing(self):
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d)
            for name in ["one", "two"]:
                (bundle / name).write_bytes(name.encode())
            first = {
                "one": {
                    "digest": "sha256:" + hashlib.sha256(b"one").hexdigest(),
                    "state": "uploaded",
                }
            }
            uploaded = []
            reconcile(bundle, first, False, uploaded.append)
            self.assertEqual(uploaded, [bundle / "two"])
            with self.assertRaises(ValueError):
                reconcile(bundle, first, True, uploaded.append)
            first["one"]["state"] = "starter"
            with self.assertRaises(ValueError):
                reconcile(bundle, first, False, uploaded.append)
            first["unexpected"] = {}
            with self.assertRaises(ValueError):
                reconcile(bundle, first, False, uploaded.append)
