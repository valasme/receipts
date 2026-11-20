import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from stage import reconcile, stage


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

    def test_new_draft_becomes_visible_after_creation(self):
        tag = "v0.0.1-pre.2"
        draft = {"tag_name": tag, "draft": True, "prerelease": True, "assets": []}
        responses = ["[[]]", "created", "[[]]", json.dumps([[draft]]), "uploaded"]
        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d)
            (bundle / "archive.zip").write_bytes(b"candidate")
            with patch.dict(os.environ, GITHUB_REPOSITORY="owner/project"), patch(
                "stage.subprocess.check_output", side_effect=responses
            ) as gh, patch("time.sleep"):
                stage(tag, bundle, bundle.parent / "notes")
            operations = [c.args[0][1:3] for c in gh.call_args_list]
            self.assertEqual(operations.count(["release", "create"]), 1)
            self.assertEqual(operations.count(["release", "upload"]), 1)
