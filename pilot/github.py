"""Opt-in GitHub adapter for the Receipts public demo repository."""

import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

MARKER = "<!-- receipts:public-demo:v1 -->"
CONSENT = "receipts:publish"
STALE = MARKER + "\nPreviously checked input changed. The previous receipt is stale."
DEMO = "valasme/receipts"


class ApiFailure(Exception):
    pass


class GitHub:
    def __init__(self, repository):
        if repository != DEMO:
            raise ValueError("pilot restricted to the public demo")
        self.base = "repos/" + repository

    def request(self, method, path, payload=None):
        args = ["gh", "api", "-X", method, self.base + path]
        data = None
        if payload is not None:
            args += ["--input", "-"]
            data = json.dumps(payload).encode()
        try:
            result = subprocess.run(
                args, check=False, input=data, capture_output=True, timeout=20
            )
        except (OSError, subprocess.TimeoutExpired) as err:
            raise ApiFailure("GitHub API unavailable") from err
        if result.returncode:
            raise ApiFailure("GitHub API request failed")
        return json.loads(result.stdout) if result.stdout.strip() else None


@dataclass(frozen=True)
class Submission:
    digest: str
    claim: dict[str, str] | None
    consent: bool
    note: str = "No supported exact-quote claim at this revision."


def submission_number(value):
    if not re.fullmatch(r"[1-9][0-9]{0,9}", value):
        raise ValueError("supply the canonical decimal submission number")
    return int(value)


def unique_fields(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate fields")
    return result


def source(api, number):
    item = api.request("GET", f"/issues/{number}")
    head, head_repo = None, None
    if "pull_request" in item:
        item = api.request("GET", f"/pulls/{number}")
        head = item["head"]["sha"]
        head_repo = (item["head"].get("repo") or {}).get("full_name")
    body = item.get("body") or ""
    # Keep the digest stable for previously published issues and same-repo PRs.
    identity = [number, body, head, item["state"]]
    if head and head_repo != DEMO:
        identity.append(head_repo)
    digest = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
    consent = CONSENT in {label["name"] for label in item["labels"]}
    if head and head_repo != DEMO:
        return Submission(digest, None, consent, "Fork or unavailable pull request source is outside the pilot cohort.")
    if len(body.encode()) > 65536 or item["state"] != "open":
        return Submission(digest, None, consent)
    blocks = re.findall(
        r"^```receipts\r?\n(.*?)\r?\n```[ \t]*\r?$", body, re.MULTILINE | re.DOTALL
    )
    if len(blocks) != 1:
        return Submission(digest, None, consent)
    try:
        claim = json.loads(blocks[0], object_pairs_hook=unique_fields)
        if (
            not isinstance(claim, dict)
            or set(claim) != {"rev", "path", "quote"}
            or not all(isinstance(x, str) for x in claim.values())
        ):
            return Submission(digest, None, consent)
        for value in claim.values():
            value.encode("utf-8")
    except (ValueError, RecursionError):
        return Submission(digest, None, consent)
    if head and claim["rev"].lower() != head:
        return Submission(digest, None, consent)
    return Submission(digest, claim, consent)


def preview(api, number, check):
    observation = source(api, number)
    receipt = check(observation.claim) if observation.claim else None
    if source(api, number).digest != observation.digest:
        return "Submission changed while checking. Retry to get a current preview.\n"
    return receipt or observation.note + "\n"


def existing(api, number):
    found = []
    for page in range(1, 5):
        comments = api.request(
            "GET", f"/issues/{number}/comments?per_page=100&page={page}"
        )
        found.extend(
            c
            for c in comments
            if c.get("user", {}).get("login") == "github-actions[bot]"
            and c.get("user", {}).get("type") == "Bot"
            and c.get("body", "").startswith(MARKER + "\n")
        )
        if len(comments) < 100:
            break
    else:
        if api.request("GET", f"/issues/{number}/comments?per_page=1&page=401"):
            raise ApiFailure("comment scan exceeded budget")
    if len(found) > 1:
        raise ApiFailure("multiple publisher comments; reconcile manually")
    return found[0] if found else None


def render(claim, executable):
    if claim is None:
        return None
    try:
        p = subprocess.run(
            [executable, "check", "--repo", ".", "--claim-file", "-", "--format", "markdown"],
            check=False,
            input=json.dumps({"schema_major": 1, **claim}).encode(),
            capture_output=True,
            timeout=8,
            env={k: os.environ[k] for k in ("PATH", "SystemRoot") if k in os.environ},
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        raise ApiFailure("checker unavailable") from err
    if p.returncode == 2:
        return None
    if p.returncode != 0 or len(p.stdout) > 8192:
        raise ApiFailure("checker failed")
    return p.stdout.decode("utf-8").replace("@", "@\u200b")


def publish(api, number, check):
    observation = source(api, number)
    digest = observation.digest
    old = existing(api, number)
    try:
        receipt = check(observation.claim) if observation.claim else None
    except ApiFailure:
        if old:
            previous = re.search(r"\nInput digest: ([a-f0-9]{64})\Z", old["body"])
            if previous and previous[1] != digest and source(api, number).digest == digest:
                path = f"/issues/comments/{int(old['id'])}"
                api.request("PATCH", path, {"body": STALE})
        raise
    if not old and not (observation.consent and receipt):
        return "suppressed or empty"
    desired = (
        MARKER + "\n" + receipt + "\nInput digest: " + digest if receipt else STALE
    )
    if old and old["body"] == desired:
        return "current"
    fresh = source(api, number)
    if fresh.digest != digest or (not old and not fresh.consent):
        return "superseded"
    if old:
        path = f"/issues/comments/{int(old['id'])}"
        api.request("PATCH", path, {"body": desired})
    else:
        # Consume the owner's one-time publish label before attempting a create.
        # A deleted comment or ambiguous timeout cannot cause an automatic repost.
        api.request("DELETE", f"/issues/{number}/labels/" + quote(CONSENT, safe=""))
        if source(api, number).digest != digest:
            return "superseded"
        try:
            created = api.request(
                "POST", f"/issues/{number}/comments", {"body": desired}
            )
        except ApiFailure:
            created = existing(api, number)
            if not created or created["body"] != desired:
                raise
        path = f"/issues/comments/{int(created['id'])}"
    if source(api, number).digest != digest:
        api.request("PATCH", path, {"body": STALE})
        return "stale"
    return "updated"


def main():
    api = GitHub(os.environ["GITHUB_REPOSITORY"])
    if api.request("GET", "")["private"]:
        raise ApiFailure("public demo required")
    number = submission_number(os.environ["SUBMISSION"])
    exe = str(Path("receipts-pilot").resolve())
    if sys.argv[1] == "preview":
        receipt = preview(api, number, lambda claim: render(claim, exe))
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(receipt)
    elif sys.argv[1] == "publish":
        print(publish(api, number, lambda claim: render(claim, exe)))
    else:
        raise ValueError("invalid mode")


if __name__ == "__main__":
    try:
        main()
    except (ApiFailure, ValueError, OSError, subprocess.TimeoutExpired):
        sys.exit(
            "Pilot stopped. Check the run permissions, event revision and service availability."
        )
