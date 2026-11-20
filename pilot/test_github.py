import json
import unittest
from github import ApiFailure, CONSENT, MARKER, STALE, publish, source


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

    def request(self, method, path, payload=None):
        if method == "GET" and path == "/issues/1":
            result = {"body": self.body, "state": "open", "labels": self.labels}
            if self.head:
                result["pull_request"] = {}
            return result
        if path == "/pulls/1":
            return {"head": {"sha": self.head}}
        if method == "GET" and "/comments?" in path:
            return self.comments
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
        self.assertIsNone(source(self.api, 1)[1])
        self.api.head = "a" * 40
        self.assertIsNotNone(source(self.api, 1)[1])
        self.api.body += "\n" + self.api.body
        self.assertIsNone(source(self.api, 1)[1])

    def test_duplicate_markers(self):
        self.post()
        self.api.comments *= 2
        with self.assertRaises(ApiFailure):
            self.post()


if __name__ == "__main__":
    unittest.main()
