from __future__ import annotations

import unittest

from harness.codes import PRECONDITION_UNCHECKED
from harness.validators_impl.preconditions import PreconditionsValidator

KOZO_NEGATIVE_COVERAGE = {
    "preconditions": {
        "missing_verification_signal": "test_fails_when_preconditions_have_missing_verification_signal",
    }
}


class PreconditionsValidatorTests(unittest.TestCase):
    def test_fails_when_preconditions_have_missing_verification_signal(self):
        bundle = {
            "todo": {
                "preconditions": ["toolchain installed"],
                "verification": {
                    "tests_run": [],
                    "invariants": [],
                    "expected_behavior": [],
                    "actual_behavior": [],
                },
            },
        }

        result = PreconditionsValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, PRECONDITION_UNCHECKED)


if __name__ == "__main__":
    unittest.main()
