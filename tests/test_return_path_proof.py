from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RETURN_PATH_PROOF_INVALID
from harness.validators_impl import return_path_proof
from harness.validators_impl.return_path_proof import ReturnPathProofValidator

KOZO_NEGATIVE_COVERAGE = {
    "return_path_proof": {
        "missing_rust_status_bits_check": "test_fails_when_rust_status_bits_check_is_missing",
        "missing_odin_status_bits_write": "test_fails_when_odin_status_bits_write_is_missing",
        "status_bits_diagnostic": "test_status_bits_failure_diagnostic_names_missing_anchor",
        "unrelated_status_bits_text": "test_unrelated_status_bits_text_does_not_satisfy_rust_check",
    }
}


class ReturnPathProofValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rust_source = return_path_proof._RUST_MAIN.read_text()
        self.kernel_source = return_path_proof._KERNEL_MAIN.read_text()

    def validate_sources(self, rust_source: str, kernel_source: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            rust_path = Path(temporary_directory) / "main.rs"
            kernel_path = Path(temporary_directory) / "main.odin"
            rust_path.write_text(rust_source)
            kernel_path.write_text(kernel_source)

            original_rust_path = return_path_proof._RUST_MAIN
            original_kernel_path = return_path_proof._KERNEL_MAIN
            return_path_proof._RUST_MAIN = rust_path
            return_path_proof._KERNEL_MAIN = kernel_path
            try:
                return ReturnPathProofValidator().validate({})
            finally:
                return_path_proof._RUST_MAIN = original_rust_path
                return_path_proof._KERNEL_MAIN = original_kernel_path

    def test_passes_when_required_return_path_anchors_exist(self):
        result = self.validate_sources(self.rust_source, self.kernel_source)

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_rust_status_bits_check_is_missing(self):
        rust_source = self.rust_source.replace(
            "    if payload.status_bits != abi::K_OK {\n"
            "        fail_heartbeat_contract();\n"
            "    }\n",
            "",
        )

        result = self.validate_sources(rust_source, self.kernel_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RETURN_PATH_PROOF_INVALID)
        self.assertEqual(result.meta["missing_anchor"], "rust_returned_status_bits_check")

    def test_fails_when_odin_status_bits_write_is_missing(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.status_bits = u32(abi.K_OK)\n",
            "",
        )

        result = self.validate_sources(self.rust_source, kernel_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RETURN_PATH_PROOF_INVALID)
        self.assertEqual(result.meta["missing_anchor"], "odin_returned_status_bits_write")

    def test_status_bits_failure_diagnostic_names_missing_anchor(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.status_bits = u32(abi.K_OK)\n",
            "",
        )

        result = self.validate_sources(self.rust_source, kernel_source)

        self.assertEqual(result.status, "fail")
        self.assertIn("odin_returned_status_bits_write", result.detail)
        self.assertIn("status_bits", result.detail)

    def test_unrelated_status_bits_text_does_not_satisfy_rust_check(self):
        rust_source = self.rust_source.replace(
            "    if payload.status_bits != abi::K_OK {\n"
            "        fail_heartbeat_contract();\n"
            "    }\n",
            "    let _status_bits_mentions_are_not_checks = payload.status_bits;\n",
        )

        result = self.validate_sources(rust_source, self.kernel_source)

        self.assertIn("status_bits", rust_source)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["missing_anchor"], "rust_returned_status_bits_check")


if __name__ == "__main__":
    unittest.main()
