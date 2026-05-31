from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import EXECUTION_PROOF_INVALID, OK
from harness.validators_impl import execution_proof
from harness.validators_impl.execution_proof import ExecutionProofValidator


class ExecutionProofValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel_source = execution_proof._KERNEL_MAIN.read_text()
        self.serial_source = execution_proof._SERIAL.read_text()

    def validate_sources(self, kernel_source: str, serial_source: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            kernel_path = Path(temporary_directory) / "main.odin"
            serial_path = Path(temporary_directory) / "serial.odin"
            kernel_path.write_text(kernel_source)
            serial_path.write_text(serial_source)

            original_kernel_path = execution_proof._KERNEL_MAIN
            original_serial_path = execution_proof._SERIAL
            execution_proof._KERNEL_MAIN = kernel_path
            execution_proof._SERIAL = serial_path
            try:
                return ExecutionProofValidator().validate({})
            finally:
                execution_proof._KERNEL_MAIN = original_kernel_path
                execution_proof._SERIAL = original_serial_path

    def test_passes_when_execution_proof_anchors_exist(self):
        result = self.validate_sources(self.kernel_source, self.serial_source)

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_nil_payload_guard_is_missing(self):
        kernel_source = self.kernel_source.replace(
            "\t\tif payload == nil {\n"
            "\t\t\treturn abi.K_INVALID\n"
            "\t\t}\n",
            "",
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, EXECUTION_PROOF_INVALID)
        self.assertEqual(result.meta["reason"], "missing_nil_guard")
        self.assertEqual(result.meta["contract_field"], "nil_payload_guard")

    def test_fails_when_heartbeat_branch_is_missing(self):
        kernel_source = self.kernel_source.replace(
            "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
            "case abi.K_SYSCALL_NOP_DEBUG_HEARTBEAT:",
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_odin_heartbeat_branch")
        self.assertEqual(result.meta["contract_field"], "heartbeat_debug_branch")

    def test_fails_when_mutations_exist_only_outside_live_heartbeat_branch(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.sequence = 0xCAFEFEEE\n",
            "",
        )
        kernel_source += (
            "\ndead_heartbeat_mutations :: proc(payload: ^abi.Heartbeat_Payload) {\n"
            "\tpayload.sequence = 0xCAFEFEEE\n"
            "\tpayload.timestamp = 0xDEADBEEF\n"
            "\tpayload.status_bits = u32(abi.K_OK)\n"
            "}\n"
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "dead_snippet_outside_live_branch")
        self.assertEqual(result.meta["contract_field"], "returned_sequence_write")

    def test_fails_when_payload_mutations_are_out_of_order(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.timestamp = 0xDEADBEEF\n"
            "\t\tpayload.status_bits = u32(abi.K_OK)\n",
            "\t\tpayload.status_bits = u32(abi.K_OK)\n"
            "\t\tpayload.timestamp = 0xDEADBEEF\n",
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "out_of_order_execution_anchor")
        self.assertEqual(result.meta["contract_field"], "returned_status_bits_write")

    def test_fails_when_returned_status_bits_mutation_is_missing(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.status_bits = u32(abi.K_OK)\n",
            "",
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_mutation")
        self.assertEqual(result.meta["contract_field"], "returned_status_bits_write")

    def test_fails_when_serial_observation_string_is_missing(self):
        serial_source = self.serial_source.replace(
            '\tserial_write("SYSCALL[DEBUG_HEARTBEAT] New Time: 0x")\n',
            "",
        )

        result = self.validate_sources(self.kernel_source, serial_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_serial_observation")
        self.assertEqual(result.meta["contract_field"], "serial_time_observation")

    def test_failure_detail_names_missing_execution_contract_field(self):
        kernel_source = self.kernel_source.replace(
            "\t\tpayload.status_bits = u32(abi.K_OK)\n",
            "",
        )

        result = self.validate_sources(kernel_source, self.serial_source)

        self.assertIn("returned_status_bits_write", result.detail)
        self.assertIn("missing_mutation", result.detail)


if __name__ == "__main__":
    unittest.main()
