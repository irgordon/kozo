from __future__ import annotations

import unittest

from harness.codes import VERIFICATION_REFS_INVALID
from harness.validators_impl.verification_refs import VerificationRefsValidator

KOZO_NEGATIVE_COVERAGE = {
    "verification_refs": {
        "invalid_verification_ref": "test_fails_when_verification_ref_is_invalid",
    }
}


class VerificationRefsValidatorTests(unittest.TestCase):
    def test_fails_when_verification_ref_is_invalid(self):
        bundle = {
            "todo": {
                "verification": {"tests_run": []},
                "steps": [
                    {"verification_refs": ["verification.not_a_section[0]"]},
                ],
            },
        }

        result = VerificationRefsValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, VERIFICATION_REFS_INVALID)


if __name__ == "__main__":
    unittest.main()
