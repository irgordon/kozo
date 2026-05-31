from __future__ import annotations

import tempfile
import unittest

from harness.codes import EVIDENCE_FILE_MISSING
from harness.validators_impl.evidence import EvidenceValidator


class EvidenceValidatorTests(unittest.TestCase):
    def test_fails_when_evidence_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = EvidenceValidator().validate(
                {
                    "root_dir": temporary_directory,
                    "evidence_files": ["artifacts/logs/missing.log"],
                }
            )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, EVIDENCE_FILE_MISSING)


if __name__ == "__main__":
    unittest.main()
