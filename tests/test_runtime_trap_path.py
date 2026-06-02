from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_TRAP_PATH_INVALID
from harness.validators_impl import runtime_trap_path
from harness.validators_impl.runtime_trap_path import RuntimeTrapPathValidator

KOZO_NEGATIVE_COVERAGE = {
    "runtime_trap_path": {
        "dead_extern_call_outside_helper": "test_fails_when_extern_call_exists_only_outside_live_bridge_helper",
        "missing_payload_construction": "test_fails_when_payload_construction_is_missing_from_live_path",
        "wrong_sequence_sentinel": "test_fails_when_request_sequence_sentinel_is_wrong",
        "wrong_timestamp_sentinel": "test_fails_when_request_timestamp_sentinel_is_wrong",
        "wrong_status_bits_initialization": "test_fails_when_request_status_bits_initialization_is_wrong",
        "out_of_order_live_path": "test_fails_when_live_path_operations_are_out_of_order",
        "missing_heartbeat_block": "test_missing_live_heartbeat_block_diagnostic_names_contract",
        "missing_nop_block": "test_fails_when_nop_request_is_missing",
        "missing_status_block": "test_fails_when_status_request_is_missing",
        "nop_hardcoded_syscall_id": "test_fails_when_nop_uses_hardcoded_syscall_id",
        "status_hardcoded_syscall_id": "test_fails_when_status_uses_hardcoded_syscall_id",
        "nop_non_null_payload": "test_fails_when_nop_bridge_uses_non_null_payload",
        "status_non_null_payload": "test_fails_when_status_bridge_uses_non_null_payload",
        "missing_nop_return_validation": "test_fails_when_nop_return_validation_is_missing",
        "missing_status_return_validation": "test_fails_when_status_return_validation_is_missing",
        "nop_payload_usage": "test_fails_when_nop_request_uses_payload_layout",
        "status_payload_usage": "test_fails_when_status_request_uses_payload_layout",
        "nop_not_invoked": "test_fails_when_core_entry_does_not_invoke_nop_probe",
        "status_not_invoked": "test_fails_when_core_entry_does_not_invoke_status_probe",
    }
}


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

    def test_fails_when_nop_request_is_missing(self):
        rust_source = self.rust_source.replace(
            "pub fn nop_request() -> abi::K_STATUS {",
            "pub fn nop_request_disabled() -> abi::K_STATUS {",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_live_nop_block")
        self.assertEqual(result.meta["contract_field"], "nop_request")

    def test_fails_when_status_request_is_missing(self):
        rust_source = self.rust_source.replace(
            "pub fn status_request() -> abi::K_STATUS {",
            "pub fn status_request_disabled() -> abi::K_STATUS {",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_live_status_block")
        self.assertEqual(result.meta["contract_field"], "status_request")

    def test_fails_when_nop_uses_hardcoded_syscall_id(self):
        rust_source = self.rust_source.replace(
            "    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_NOP;\n",
            "    let syscall: abi::K_SYSCALL_ID = 0;\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_runtime_anchor")
        self.assertEqual(result.meta["contract_field"], "nop_syscall_constant")

    def test_fails_when_status_uses_hardcoded_syscall_id(self):
        rust_source = self.rust_source.replace(
            "    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_STATUS;\n",
            "    let syscall: abi::K_SYSCALL_ID = 2;\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_runtime_anchor")
        self.assertEqual(result.meta["contract_field"], "status_syscall_constant")

    def test_fails_when_nop_bridge_uses_non_null_payload(self):
        rust_source = self.rust_source.replace(
            "fn invoke_no_payload_bridge(syscall: abi::K_SYSCALL_ID) -> abi::K_STATUS {\n"
            "    unsafe { syscall_entry(u64::from(syscall), core::ptr::null_mut()) as abi::K_STATUS }\n"
            "}\n",
            "fn invoke_no_payload_bridge(syscall: abi::K_SYSCALL_ID) -> abi::K_STATUS {\n"
            "    let mut payload = abi::HeartbeatPayload { sequence: 0, timestamp: 0, status_bits: abi::K_INVALID };\n"
            "    unsafe { syscall_entry(u64::from(syscall), &mut payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }\n"
            "}\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "forbidden_nop_payload_usage")
        self.assertEqual(result.meta["contract_field"], "nop_payload_construction")

    def test_fails_when_status_bridge_uses_non_null_payload(self):
        rust_source = self.rust_source.replace(
            "fn invoke_no_payload_bridge(syscall: abi::K_SYSCALL_ID) -> abi::K_STATUS {\n"
            "    unsafe { syscall_entry(u64::from(syscall), core::ptr::null_mut()) as abi::K_STATUS }\n"
            "}\n",
            "fn invoke_no_payload_bridge(syscall: abi::K_SYSCALL_ID) -> abi::K_STATUS {\n"
            "    let mut payload = abi::HeartbeatPayload { sequence: 0, timestamp: 0, status_bits: abi::K_INVALID };\n"
            "    unsafe { syscall_entry(u64::from(syscall), &mut payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }\n"
            "}\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "forbidden_nop_payload_usage")
        self.assertEqual(result.meta["contract_field"], "nop_payload_construction")

    def test_fails_when_nop_return_validation_is_missing(self):
        rust_source = self.rust_source.replace(
            "    return validate_nop_return_status(status);\n",
            "    return status;\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "nop_return_validation")

    def test_fails_when_status_return_validation_is_missing(self):
        rust_source = self.rust_source.replace(
            "    return validate_status_return_status(status);\n",
            "    return status;\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "status_return_validation")

    def test_fails_when_nop_request_uses_payload_layout(self):
        rust_source = self.rust_source.replace(
            "pub fn nop_request() -> abi::K_STATUS {\n",
            "pub fn nop_request() -> abi::K_STATUS {\n"
            "    let _payload = abi::HeartbeatPayload { sequence: 0, timestamp: 0, status_bits: abi::K_INVALID };\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "forbidden_nop_payload_usage")
        self.assertEqual(result.meta["contract_field"], "nop_payload_construction")

    def test_fails_when_status_request_uses_payload_layout(self):
        rust_source = self.rust_source.replace(
            "pub fn status_request() -> abi::K_STATUS {\n",
            "pub fn status_request() -> abi::K_STATUS {\n"
            "    let _payload = abi::HeartbeatPayload { sequence: 0, timestamp: 0, status_bits: abi::K_INVALID };\n",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "forbidden_nop_payload_usage")
        self.assertEqual(result.meta["contract_field"], "status_payload_construction")

    def test_fails_when_core_entry_does_not_invoke_nop_probe(self):
        rust_source = self.rust_source.replace(
            "    let _ = nop_request();\n",
            "",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "core_entry_nop_probe")

    def test_fails_when_core_entry_does_not_invoke_status_probe(self):
        rust_source = self.rust_source.replace(
            "    let _ = status_request();\n",
            "",
        )

        result = self.validate_source(rust_source)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["contract_field"], "core_entry_status_probe")


if __name__ == "__main__":
    unittest.main()
