from __future__ import annotations

import unittest

from harness.codes import EXPLANATION_SUMMARY_REQUIRED
from harness.validators_impl.explanation import ExplanationValidator

KOZO_NEGATIVE_COVERAGE = {
    "explanation": {
        "missing_explanation_summary": "test_fails_when_complete_plan_has_missing_explanation",
    }
}


class ExplanationValidatorTests(unittest.TestCase):
    def test_fails_when_complete_plan_has_missing_explanation(self):
        bundle = {
            "todo": {
                "plan_status": "complete",
                "steps": [],
                "explanation_summary": [],
            },
        }

        result = ExplanationValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, EXPLANATION_SUMMARY_REQUIRED)


if __name__ == "__main__":
    unittest.main()
