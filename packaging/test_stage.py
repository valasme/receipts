import hashlib
import json
import os
import subprocess
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

    def test_retry_after_upload_response_is_lost(self):
        tag = "v0.0.1-pre.2"
        draft = {"tag_name": tag, "draft": True, "prerelease": True, "assets": []}
        uploaded = []

        def gh(args, **kwargs):
            if args[1] == "api":
                return json.dumps([[draft]])
            self.assertEqual(args[1:4], ["release", "upload", tag])
            path = Path(args[4])
            uploaded.append(path.name)
            draft["assets"].append({
                "name": path.name,
                "digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "state": "uploaded",
            })
            if len(uploaded) == 1:
                raise subprocess.CalledProcessError(1, args)
            return ""

        with tempfile.TemporaryDirectory() as d:
            bundle = Path(d)
            for name in ("one", "two"):
                (bundle / name).write_bytes(name.encode())
            with patch.dict(os.environ, GITHUB_REPOSITORY="owner/project"), patch(
                "stage.subprocess.check_output", side_effect=gh
            ):
                with self.assertRaises(subprocess.CalledProcessError):
                    stage(tag, bundle, bundle / "notes")
                stage(tag, bundle, bundle / "notes")
                draft["draft"] = False
                stage(tag, bundle, bundle / "notes")
                draft["assets"][0]["digest"] = "sha256:" + "0" * 64
                with self.assertRaisesRegex(ValueError, "differs"):
                    stage(tag, bundle, bundle / "notes")
        self.assertEqual(uploaded, ["one", "two"])
