from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_TRAP_PATH_INVALID
from harness.validators_impl import runtime_trap_path
from harness.validators_impl.runtime_trap_path import RuntimeTrapPathValidator


class RuntimeTrapPathValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rust_source = runtime_trap_path._SERVICE_PATH.read_text()

    def validate_source(self, rust_source: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            rust_path = Path(temporary_directory) / "main.rs"
            rust_path.write_text(rust_source)

            original_service_path = runtime_trap_path._SERVICE_PATH
            runtime_trap_path._SERVICE_PATH = rust_path
            try:
                return RuntimeTrapPathValidator().validate({})
            finally:
                runtime_trap_path._SERVICE_PATH = original_service_path

    def test_passes_when_live_heartbeat_path_has_ordered_runtime_anchors(self):
        result = self.validate_source(self.rust_source)

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_extern_call_exists_only_outside_live_bridge_helper(self):
        rust_source = self.rust_source.replace(
            "    unsafe { syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }\n",
            "    let _ = syscall;\n"
            "    let _ = payload;\n"
            "    0 as abi::K_STATUS\n",
        )
        rust_source += (
            "\nfn dead_syscall_entry_call(syscall: abi::K_SYSCALL_ID, payload: &mut abi::HeartbeatPayload) -> abi::K_STATUS {\n"
            "    unsafe { syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }\n"
            "}\n"
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_TRAP_PATH_INVALID)
        self.assertEqual(result.meta["reason"], "dead_snippet_outside_live_path")
        self.assertEqual(result.meta["contract_field"], "extern_bridge_call")

    def test_fails_when_payload_construction_is_missing_from_live_path(self):
        rust_source = self.rust_source.replace(
            "    let mut payload = abi::HeartbeatPayload {\n",
            "",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_runtime_anchor")
        self.assertEqual(result.meta["contract_field"], "payload_initialization")

    def test_fails_when_request_sequence_sentinel_is_wrong(self):
        rust_source = self.rust_source.replace(
            "        sequence: 0xCAFEFEED,\n",
            "        sequence: 0xBADFEED,\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "request_sequence_sentinel")

    def test_fails_when_request_timestamp_sentinel_is_wrong(self):
        rust_source = self.rust_source.replace(
            "        timestamp: 0,\n",
            "        timestamp: 1,\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "request_timestamp_sentinel")

    def test_fails_when_request_status_bits_initialization_is_wrong(self):
        rust_source = self.rust_source.replace(
            "        status_bits: abi::K_INVALID,\n",
            "        status_bits: abi::K_OK,\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "request_status_bits_initialization")

    def test_fails_when_live_path_operations_are_out_of_order(self):
        rust_source = self.rust_source.replace(
            "        sequence: 0xCAFEFEED,\n"
            "        timestamp: 0,\n",
            "        timestamp: 0,\n"
            "        sequence: 0xCAFEFEED,\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "out_of_order_runtime_anchor")
        self.assertEqual(result.meta["contract_field"], "request_timestamp_sentinel")

    def test_missing_live_heartbeat_block_diagnostic_names_contract(self):
        rust_source = self.rust_source.replace(
            "pub fn heartbeat_request() -> abi::K_STATUS {",
            "pub fn heartbeat_request_disabled() -> abi::K_STATUS {",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_live_heartbeat_block")
        self.assertEqual(result.meta["contract_field"], "heartbeat_request")


if __name__ == "__main__":
    unittest.main()
