import json
import unittest

from github import (
    CONSENT,
    DEMO,
    MARKER,
    STALE,
    ApiFailure,
    existing,
    preview,
    publish,
    reconcile,
    source,
    submission_number,
)


class Demo:
    def __init__(self):
        self.body = (
            "```receipts\n"
            + json.dumps({"rev": "a" * 40, "path": "a.txt", "quote": "a"})
            + "\n```"
        )
        self.labels = [{"name": CONSENT}]
        self.comments = []
        self.race = False
        self.ambiguous = False
        self.head = None
        self.fork = False
        self.issue_body = None

    def request(self, method, path, payload=None):
        if method == "GET" and path == "/issues/1":
            result = {"body": self.issue_body or self.body, "state": "open", "labels": self.labels}
            if self.head:
                result["pull_request"] = {}
            return result
        if path == "/pulls/1":
            return {
                "body": self.body, "state": "open", "labels": self.labels,
                "head": {"sha": self.head, "repo": {"full_name": "someone/fork" if self.fork else DEMO}},
            }
        if method == "GET" and "/comments?" in path:
            limit, page = map(int, (path.split("per_page=")[1].split("&page=")))
            return self.comments[(page - 1) * limit:page * limit]
        if method == "DELETE":
            self.labels = []
            return
        if method == "POST":
            comment = {
                "id": 2,
                "body": payload["body"],
                "user": {"login": "github-actions[bot]", "type": "Bot"},
            }
            self.comments.append(comment)
            if self.race:
                self.body = ""
            if self.ambiguous:
                raise ApiFailure("timeout")
            return comment
        if method == "PATCH" and path == "/issues/comments/2":
            self.comments[-1].update(payload)
            return self.comments[-1]
        raise AssertionError((method, path))


class Publication(unittest.TestCase):
    def setUp(self):
        self.api = Demo()

    def post(self):
        return publish(self.api, 1, lambda c: "    Verified" if c else None)

    def test_refresh_suppress_and_stale(self):
        self.assertEqual(self.post(), "updated")
        self.assertEqual(self.post(), "current")
        self.api.body = ""
        self.assertEqual(self.post(), "updated")
        self.assertEqual(self.api.comments[0]["body"], STALE)
        self.api.comments.clear()
        self.assertEqual(self.post(), "suppressed or empty")

    def test_spoof_and_ambiguous_create(self):
        self.api.comments.append(
            {
                "id": 9,
                "body": MARKER + "\nfake",
                "user": {"login": "someone", "type": "User"},
            }
        )
        self.api.ambiguous = True
        self.assertEqual(self.post(), "updated")
        self.assertEqual(self.post(), "current")
        self.assertEqual(len(self.api.comments), 2)

    def test_race(self):
        self.api.race = True
        self.assertEqual(self.post(), "stale")
        self.assertEqual(self.api.comments[0]["body"], STALE)

    def test_deleted_comment(self):
        self.post()
        self.api.comments.clear()
        self.assertEqual(self.post(), "suppressed or empty")

    def test_multiple_blocks_and_head_change(self):
        self.api.head = "b" * 40
        self.assertIsNone(source(self.api, 1).claim)
        self.api.head = "a" * 40
        self.assertIsNotNone(source(self.api, 1).claim)
        self.api.body += "\n" + self.api.body
        self.assertIsNone(source(self.api, 1).claim)

    def test_checker_failure_retires_only_changed_receipt(self):
        def fail(_):
            raise ApiFailure("checker unavailable")

        self.assertEqual(self.post(), "updated")
        body = self.api.comments[0]["body"]
        with self.assertRaises(ApiFailure):
            publish(self.api, 1, fail)
        self.assertEqual(self.api.comments[0]["body"], body)
        self.api.body += "\nUpdated."
        with self.assertRaises(ApiFailure):
            publish(self.api, 1, fail)
        self.assertEqual(self.api.comments[0]["body"], STALE)

    def test_failed_preview_can_only_retire_stale_owned_receipt(self):
        self.assertEqual(reconcile(self.api, 1), "current or empty")
        self.assertEqual(self.api.comments, [])
        self.assertEqual(self.post(), "updated")
        self.assertEqual(reconcile(self.api, 1), "current or empty")
        self.api.body += "\nUpdated."
        self.assertEqual(reconcile(self.api, 1), "stale")
        self.assertEqual([entry["body"] for entry in self.api.comments], [STALE])

    def test_checker_failure_after_second_edit_retires_old_receipt(self):
        self.assertEqual(self.post(), "updated")
        self.api.body += "\nFirst update."

        def fail(_):
            self.api.body += "\nSecond update."
            raise ApiFailure("checker unavailable")

        with self.assertRaises(ApiFailure):
            publish(self.api, 1, fail)
        self.assertEqual(self.api.comments[0]["body"], STALE)

    def test_pr_uses_authoritative_snapshot_and_revalidates_preview(self):
        self.api.head = "b" * 40
        self.api.issue_body = self.api.body
        self.api.body = self.api.body.replace("a" * 40, self.api.head)
        self.assertEqual(source(self.api, 1).claim["rev"], self.api.head)

        def render(_):
            self.api.head = "c" * 40
            return "Verified"

        self.assertIn("changed while checking", preview(self.api, 1, render))

    def test_fork_is_ineligible_without_loading_objects(self):
        self.api.head = "a" * 40
        self.api.fork = True
        self.assertIn("Fork", preview(self.api, 1, lambda _: self.fail("checker invoked")))

    def test_admission_rejects_duplicate_keys_and_unpaired_surrogates(self):
        self.api.body = self.api.body.replace('"quote": "a"', '"quote": "a", "quote": "b"')
        self.assertIsNone(source(self.api, 1).claim)
        self.api.body = self.api.body.replace('"quote": "a", "quote": "b"', r'"quote": "\ud800"')
        self.assertIsNone(source(self.api, 1).claim)

    def test_comment_budget(self):
        for length in (399, 400):
            self.api.comments = [{}] * length
            self.assertIsNone(existing(self.api, 1))
        self.api.comments = [{}] * 401
        with self.assertRaises(ApiFailure):
            existing(self.api, 1)

    def test_only_canonical_submission_ids(self):
        self.assertEqual(submission_number("12"), 12)
        for value in ("", "0", "012", "+12", "12 ", "1e1", "１２"):
            with self.assertRaises(ValueError):
                submission_number(value)

    def test_duplicate_markers(self):
        self.post()
        self.api.comments *= 2
        with self.assertRaises(ApiFailure):
            self.post()


if __name__ == "__main__":
    unittest.main()
