from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import PROTOCOL_MISMATCH
from harness.validators_impl import protocol_validator
from harness.validators_impl.protocol_validator import ProtocolContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "protocol_contract_alignment": {
        "missing_manifest_syscall_constant": "test_fails_when_manifest_syscall_constant_is_missing",
        "manifest_syscall_value_mismatch": "test_fails_when_manifest_syscall_value_mismatches_bindings",
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

    def test_fails_when_manifest_syscall_constant_is_missing(self):
        result = self.validate_contract(
            manifest=self.valid_manifest_without_debug_heartbeat
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "missing_manifest_syscall_constant", "constants.syscalls.K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_manifest_syscall_value_mismatches_bindings(self):
        result = self.validate_contract(
            manifest=self.valid_manifest_with_wrong_heartbeat_value
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "rust_mismatched_generated_syscall_constant", "rust_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_generated_rust_syscall_constant_is_missing(self):
        result = self.validate_contract(
            rust_bindings=self.valid_rust_bindings().replace(
                "pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "rust_missing_generated_syscall_constant", "rust_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_generated_rust_nop_syscall_constant_is_missing(self):
        result = self.validate_contract(
            rust_bindings=self.valid_rust_bindings().replace(
                "pub const K_SYSCALL_NOP: K_SYSCALL_ID = 0;\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "rust_missing_generated_syscall_constant", "rust_K_SYSCALL_NOP")

    def test_fails_when_generated_odin_syscall_constant_is_missing(self):
        result = self.validate_contract(
            odin_bindings=self.valid_odin_bindings().replace(
                "K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "odin_missing_generated_syscall_constant", "odin_K_SYSCALL_DEBUG_HEARTBEAT")

    def test_fails_when_generated_odin_nop_syscall_constant_is_missing(self):
        result = self.validate_contract(
            odin_bindings=self.valid_odin_bindings().replace(
                "K_SYSCALL_NOP : K_SYSCALL_ID : 0\n",
                "",
            )
        )

        self.assertEqual(result.status, "fail")

        self.assert_protocol_failure(result, "odin_missing_generated_syscall_constant", "odin_K_SYSCALL_NOP")

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
        manifest=None,
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
            manifest_data = manifest(paths) if manifest is not None else self.valid_manifest(paths)
            paths["manifest"] = self.write_manifest(root, manifest_data)
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

    def write_manifest(self, root: Path, manifest: dict[str, object]) -> Path:
        manifest_path = root / "kozo_abi_manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        return manifest_path

    def capture_protocol_paths(self) -> dict[str, Path]:
        return {
            "manifest": protocol_validator._ABI_MANIFEST_PATH,
            "kernel": protocol_validator._KERNEL_PATH,
            "service": protocol_validator._SERVICE_PATH,
        }

    def install_protocol_paths(self, paths: dict[str, Path]) -> None:
        protocol_validator._ABI_MANIFEST_PATH = paths["manifest"]
        protocol_validator._KERNEL_PATH = paths["kernel"]
        protocol_validator._SERVICE_PATH = paths["service"]

    def restore_protocol_paths(self, paths: dict[str, Path]) -> None:
        protocol_validator._ABI_MANIFEST_PATH = paths["manifest"]
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

    def valid_manifest(self, paths: dict[str, Path]) -> dict[str, object]:
        return {
            "version": 0,
            "canonical_header": str(paths["header"]),
            "generated_bindings": {
                "rust": str(paths["rust_bindings"]),
                "odin": str(paths["odin_bindings"]),
            },
            "constants": {
                "status": {
                    "K_OK": 0,
                    "K_INVALID": 1,
                },
                "syscalls": {
                    "K_SYSCALL_NOP": 0,
                    "K_SYSCALL_DEBUG_HEARTBEAT": 1,
                },
            },
            "layouts": {
                "heartbeat_payload": {
                    "c_name": "k_heartbeat_payload_t",
                    "rust_name": "HeartbeatPayload",
                    "odin_name": "Heartbeat_Payload",
                    "size": 24,
                    "alignment": 8,
                    "fields": [
                        {"name": "sequence", "width": 8, "offset": 0},
                        {"name": "timestamp", "width": 8, "offset": 8},
                        {"name": "status_bits", "width": 4, "offset": 16},
                    ],
                }
            },
            "heartbeat": {
                "request": {
                    "sequence": "0xCAFEFEED",
                    "timestamp": 0,
                    "status_bits": "K_INVALID",
                },
                "response": {
                    "sequence": "0xCAFEFEEE",
                    "timestamp": "0xDEADBEEF",
                    "status_bits": "K_OK",
                },
            },
        }

    def valid_manifest_without_debug_heartbeat(self, paths: dict[str, Path]) -> dict[str, object]:
        manifest = self.valid_manifest(paths)
        del manifest["constants"]["syscalls"]["K_SYSCALL_DEBUG_HEARTBEAT"]
        return manifest

    def valid_manifest_with_wrong_heartbeat_value(self, paths: dict[str, Path]) -> dict[str, object]:
        manifest = self.valid_manifest(paths)
        manifest["constants"]["syscalls"]["K_SYSCALL_DEBUG_HEARTBEAT"] = 2
        return manifest


if __name__ == "__main__":
    unittest.main()
