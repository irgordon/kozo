from __future__ import annotations

import unittest

from harness.codes import RUST_TEST_FAILED
from harness.validators_impl.rust import RustValidator

KOZO_NEGATIVE_COVERAGE = {
    "rust": {
        "missing_cargo_evidence": "test_fails_when_rust_change_has_missing_cargo_evidence",
    }
}


class RustValidatorTests(unittest.TestCase):
    def test_fails_when_rust_change_has_missing_cargo_evidence(self):
        bundle = {
            "todo": {"verification": {"tests_run": [], "logs": []}},
            "changed_files": ["userspace/core_service/src/main.rs"],
            "evidence_files": [],
        }

        result = RustValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUST_TEST_FAILED)


if __name__ == "__main__":
    unittest.main()
