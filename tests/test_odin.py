from __future__ import annotations

import unittest

from harness.codes import ODIN_CHECK_FAILED
from harness.validators_impl.odin import OdinValidator


class OdinValidatorTests(unittest.TestCase):
    def test_fails_when_odin_change_has_missing_check_evidence(self):
        bundle = {
            "todo": {"verification": {"tests_run": [], "logs": []}},
            "changed_files": ["kernel/main.odin"],
            "evidence_files": [],
        }

        result = OdinValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, ODIN_CHECK_FAILED)


if __name__ == "__main__":
    unittest.main()
