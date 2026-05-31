from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import PROTOCOL_MISMATCH
from harness.validators_impl import protocol_validator
from harness.validators_impl.protocol_validator import ProtocolContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "protocol_contract_alignment": {
        "missing_rust_syscall_constant": "test_fails_when_generated_rust_syscall_constant_is_missing",
        "missing_odin_syscall_constant": "test_fails_when_generated_odin_syscall_constant_is_missing",
        "rust_hardcoded_syscall_id": "test_fails_when_rust_uses_hardcoded_syscall_id",
        "odin_hardcoded_syscall_id": "test_fails_when_odin_uses_hardcoded_syscall_id",
        "constant_mismatch": "test_fails_when_generated_syscall_constants_disagree",
        "dead_or_stale_constant": "test_fails_when_stale_constant_exists_outside_live_rust_path",
        "diagnostic_names_protocol_field": "test_failure_diagnostic_names_protocol_field",
    }
}


class ProtocolContractValidatorTests(unittest.TestCase):
    def test_passes_when_protocol_contract_is_aligned(self):
        result = self.validate_contract()

        self.assertEqual(result.status, "pass")

    def test_fails_when_generated_rust_syscall_constant_is_missing(self):
        result = self.validate_contract(
            rust_bindings=self.valid_rust_bindings().replace(
                "pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "rust_missing_generated_syscall_constant", "rust_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_generated_odin_syscall_constant_is_missing(self):
        result = self.validate_contract(
            odin_bindings=self.valid_odin_bindings().replace(
                "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "odin_missing_generated_syscall_constant", "odin_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_rust_uses_hardcoded_syscall_id(self):
        result = self.validate_contract(
            service=self.valid_service().replace(
                "let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;",
                "let syscall: abi::K_SYSCALL_ID = 1;",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "hardcoded_syscall_id", "rust_hardcoded_heartbeat_syscall_id")

    def test_fails_when_odin_uses_hardcoded_syscall_id(self):
        result = self.validate_contract(
            kernel=self.valid_kernel().replace(
                "syscall_dispatch(abi.K_SYSCALL_DEBUG_HEARTBEAT, heartbeat_payload_from_handle(handle))",
                "syscall_dispatch(1, heartbeat_payload_from_handle(handle))",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "hardcoded_syscall_id", "odin_hardcoded_heartbeat_syscall_id")

    def test_fails_when_generated_syscall_constants_disagree(self):
        result = self.validate_contract(
            odin_bindings=self.valid_odin_bindings().replace(
                "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1",
                "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 2",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "odin_mismatched_generated_syscall_constant", "odin_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_stale_constant_exists_outside_live_rust_path(self):
        result = self.validate_contract(
            service=self.valid_service().replace(
                "let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;",
                "let syscall: abi::K_SYSCALL_ID = 1;",
            )
            + "\nfn stale_reference() { let _ = abi::K_SYSCALL_DEBUG_HEARTBEAT; }\n"
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "hardcoded_syscall_id", "rust_hardcoded_heartbeat_syscall_id")

    def test_failure_diagnostic_names_protocol_field(self):
        result = self.validate_contract(
            kernel=self.valid_kernel().replace(
                "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
                "case abi.K_SYSCALL_DEBUG_HEARTBEAT_DISABLED:",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "missing_odin_syscall_case", "K_SYSCALL_DEBUG_HEARTBEAT")

    def validate_contract(
        self,
        *,
        header: str | None = None,
        rust_bindings: str | None = None,
        odin_bindings: str | None = None,
        kernel: str | None = None,
        service: str | None = None,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_contract_files(
                root,
                header or self.valid_header(),
                rust_bindings or self.valid_rust_bindings(),
                odin_bindings or self.valid_odin_bindings(),
                kernel or self.valid_kernel(),
                service or self.valid_service(),
            )
            original_paths = self.capture_protocol_paths()
            self.install_protocol_paths(paths)
            try:
                return ProtocolContractValidator().validate({})
            finally:
                self.restore_protocol_paths(original_paths)

    def write_contract_files(
        self,
        root: Path,
        header: str,
        rust_bindings: str,
        odin_bindings: str,
        kernel: str,
        service: str,
    ) -> dict[str, Path]:
        paths = {
            "header": root / "kozo_abi.h",
            "rust_bindings": root / "kozo_abi.rs",
            "odin_bindings": root / "kozo_abi.odin",
            "kernel": root / "main.odin",
            "service": root / "main.rs",
        }
        paths["header"].write_text(header)
        paths["rust_bindings"].write_text(rust_bindings)
        paths["odin_bindings"].write_text(odin_bindings)
        paths["kernel"].write_text(kernel)
        paths["service"].write_text(service)
        return paths

    def capture_protocol_paths(self) -> dict[str, Path]:
        return {
            "header": protocol_validator._HEADER_PATH,
            "rust_bindings": protocol_validator._RUST_BINDINGS_PATH,
            "odin_bindings": protocol_validator._ODIN_BINDINGS_PATH,
            "kernel": protocol_validator._KERNEL_PATH,
            "service": protocol_validator._SERVICE_PATH,
        }

    def install_protocol_paths(self, paths: dict[str, Path]) -> None:
        protocol_validator._HEADER_PATH = paths["header"]
        protocol_validator._RUST_BINDINGS_PATH = paths["rust_bindings"]
        protocol_validator._ODIN_BINDINGS_PATH = paths["odin_bindings"]
        protocol_validator._KERNEL_PATH = paths["kernel"]
        protocol_validator._SERVICE_PATH = paths["service"]

    def restore_protocol_paths(self, paths: dict[str, Path]) -> None:
        protocol_validator._HEADER_PATH = paths["header"]
        protocol_validator._RUST_BINDINGS_PATH = paths["rust_bindings"]
        protocol_validator._ODIN_BINDINGS_PATH = paths["odin_bindings"]
        protocol_validator._KERNEL_PATH = paths["kernel"]
        protocol_validator._SERVICE_PATH = paths["service"]

    def assert_protocol_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, PROTOCOL_MISMATCH)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)

    def valid_header(self) -> str:
        return (
            "typedef enum k_syscall_id_t {\n"
            "\tK_SYSCALL_NOP = 0,\n"
            "\tK_SYSCALL_DEBUG_HEARTBEAT = 1,\n"
            "} k_syscall_id_t;\n"
        )

    def valid_rust_bindings(self) -> str:
        return (
            "pub type K_SYSCALL_ID = u32;\n"
            "pub const K_SYSCALL_NOP: K_SYSCALL_ID = 0;\n"
            "pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;\n"
        )

    def valid_odin_bindings(self) -> str:
        return (
            "K_SYSCALL_ID :: u32\n"
            "K_SYSCALL_NOP : K_SYSCALL_ID : 0\n"
            "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1\n"
        )

    def valid_kernel(self) -> str:
        return (
            "signal_kernel_heartbeat :: proc() -> abi.K_STATUS {\n"
            "\thandle := abi.K_HANDLE(0)\n"
            "\treturn syscall_dispatch(abi.K_SYSCALL_DEBUG_HEARTBEAT, heartbeat_payload_from_handle(handle))\n"
            "}\n"
            "syscall_dispatch :: proc \"c\" (id: abi.K_SYSCALL_ID, payload: ^abi.Heartbeat_Payload) -> abi.K_STATUS {\n"
            "\tswitch id {\n"
            "\tcase abi.K_SYSCALL_NOP:\n"
            "\t\treturn abi.K_OK\n"
            "\tcase abi.K_SYSCALL_DEBUG_HEARTBEAT:\n"
            "\t\treturn abi.K_OK\n"
            "\t}\n"
            "\treturn abi.K_INVALID\n"
            "}\n"
        )

    def valid_service(self) -> str:
        return (
            'extern "C" { fn syscall_entry(id: u64, payload: *mut abi::HeartbeatPayload) -> u64; }\n'
            "fn invoke_heartbeat_bridge(syscall: abi::K_SYSCALL_ID, payload: &mut abi::HeartbeatPayload) -> abi::K_STATUS {\n"
            "    unsafe { syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }\n"
            "}\n"
            "pub fn heartbeat_request() -> abi::K_STATUS {\n"
            "    let mut payload = abi::HeartbeatPayload { sequence: 0xCAFEFEED, timestamp: 0, status_bits: abi::K_INVALID };\n"
            "    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;\n"
            "    return invoke_heartbeat_bridge(syscall, &mut payload);\n"
            "}\n"
        )


if __name__ == "__main__":
    unittest.main()
