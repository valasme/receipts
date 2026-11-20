"""Run Git fixture commands with an isolated configuration and a deadline."""

import os
import subprocess
from pathlib import Path

env = dict(
    {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")},
    GIT_CONFIG_NOSYSTEM="1",
    GIT_CONFIG_GLOBAL=os.devnull,
    GIT_AUTHOR_NAME="Fixture",
    GIT_AUTHOR_EMAIL="test@example.invalid",
    GIT_COMMITTER_NAME="Fixture",
    GIT_COMMITTER_EMAIL="test@example.invalid",
    GIT_AUTHOR_DATE="2025-01-01T00:00:00Z",
    GIT_COMMITTER_DATE="2025-01-01T00:00:00Z",
)


def git_bytes(repo, *args, data=None):
    command = ["git", "-C", str(repo), *args]
    try:
        return subprocess.check_output(command, input=data, env=env, timeout=20)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Git fixture {Path(repo).name}: {args[0]} timed out") from error


def git(repo, *args):
    return git_bytes(repo, *args).strip().decode()
