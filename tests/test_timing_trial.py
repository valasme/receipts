import random
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import timing_trial


class TimingTrialTests(unittest.TestCase):
    def test_trial_arms_are_counterbalanced_and_have_independent_verdicts(self):
        with patch("timing_trial.secrets.SystemRandom", return_value=random.Random(7)):
            tasks = list(timing_trial.trials())
        self.assertEqual(Counter(mode for _, sequence, mode, _, _ in tasks if sequence == 1),
                         {"manual": 6, "receipts": 6})
        for mode in ("manual", "receipts"):
            self.assertEqual(
                Counter(verdict for _, _, assigned, _, verdict in tasks if mode == assigned),
                {"verified": 4, "contradicted": 8},
            )
        self.assertTrue(any(a[-1] != b[-1] for a, b in zip(tasks[::2], tasks[1::2])))

    def test_timing_includes_pinned_evidence(self):
        commit, blob = "a" * 40, "b" * 40
        answers = iter(("", "verified", commit, blob))
        with tempfile.TemporaryDirectory() as directory, patch(
            "timing_trial.git", side_effect=("", "", "", "", "", commit, blob)
        ), patch("timing_trial.time.monotonic", side_effect=(10, 15)) as clock:
            def answer(prompt):
                if "observed" in prompt:
                    self.assertEqual(clock.call_count, 1)
                return next(answers)

            with patch("builtins.input", side_effect=answer):
                sample = timing_trial.task(1, 1, "manual", 30, "verified", Path(directory))
            self.assertTrue(sample["correct"])
            self.assertEqual(sample["seconds"], 5)

    def test_fast_incorrect_or_incomplete_pairs_do_not_qualify(self):
        outcomes = [
            {"pair": pair, "mode": mode, "seconds": elapsed, "status": "completed", "correct": False}
            for pair in range(1, 13)
            for mode, elapsed in (("manual", 10), ("receipts", 1))
        ]
        self.assertEqual(timing_trial.summarize(outcomes), (12, 0, 0.9, False))
        self.assertEqual(timing_trial.summarize(outcomes[:1]), (0, 0, None, False))
