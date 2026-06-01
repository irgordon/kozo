from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import SYSCALL_BOUNDARY_CONTRACT_INVALID
from harness.validators_impl import syscall_boundary_contract
from harness.validators_impl.syscall_boundary_contract import SyscallBoundaryContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_boundary_contract": {
        "missing_contract_file": "test_fails_when_contract_file_is_missing",
        "invalid_json": "test_fails_when_contract_json_is_invalid",
        "schema_violation": "test_fails_when_contract_schema_is_invalid",
        "wrong_architecture": "test_fails_when_architecture_is_wrong",
        "missing_assembly_path": "test_fails_when_assembly_path_is_missing",
        "wrong_entry_symbol": "test_fails_when_entry_symbol_is_wrong",
        "wrong_syscall_id_register": "test_fails_when_syscall_id_register_is_wrong",
        "wrong_payload_register": "test_fails_when_payload_register_is_wrong",
        "wrong_return_register": "test_fails_when_return_register_is_wrong",
        "missing_abi_syscall_constant": "test_fails_when_abi_syscall_constant_is_missing",
        "missing_nop_syscall_constant": "test_fails_when_nop_syscall_constant_is_missing",
        "wrong_nop_payload_argument": "test_fails_when_nop_payload_argument_is_not_null",
        "wrong_nop_return_status": "test_fails_when_nop_return_status_is_wrong",
        "nop_mutates_payload": "test_fails_when_nop_mutates_payload",
        "missing_payload_layout": "test_fails_when_payload_layout_is_missing",
        "request_sentinel_mismatch": "test_fails_when_request_sentinel_mismatches_manifest",
        "response_sentinel_mismatch": "test_fails_when_response_sentinel_mismatches_manifest",
        "unknown_status_constant": "test_fails_when_invalid_behavior_uses_unknown_status",
        "unknown_mutable_field": "test_fails_when_mutable_field_is_unknown",
        "payload_retention_forbidden": "test_fails_when_kernel_payload_retention_is_enabled",
        "unknown_proof_validator": "test_fails_when_proof_ownership_references_unknown_validator",
        "diagnostic_names_contract_field": "test_failure_diagnostic_names_contract_field",
    }
}


class SyscallBoundaryContractValidatorTests(unittest.TestCase):
    def test_passes_when_boundary_contract_matches_manifest_and_bridge(self):
        result = self.validate_boundary_contract()

        self.assertEqual(result.status, "pass")

    def test_fails_when_contract_file_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_boundary_fixture(root)
            paths["contract"] = root / "missing.json"

            result = self.validate_with_paths(paths)

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_boundary_contract(contract_text="{")

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_invalid(self):
        result = self.validate_boundary_contract(contract={"version": 0})

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_architecture_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("architecture",), "aarch64")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_architecture", "architecture")

    def test_fails_when_assembly_path_is_missing(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("entry", "assembly_path"), "/missing/syscall.asm")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "missing_assembly_path", "entry.assembly_path")

    def test_fails_when_entry_symbol_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("entry", "symbol"), "wrong_syscall_entry")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_entry_symbol", "entry.symbol")

    def test_fails_when_syscall_id_register_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "syscall_id", "register"), "rax")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_syscall_id_register", "calling_convention.syscall_id.register")

    def test_fails_when_payload_register_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "payload", "register"), "rdx")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_payload_register", "calling_convention.payload.register")

    def test_fails_when_return_register_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "return", "register"), "rbx")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_return_register", "calling_convention.return.register")

    def test_fails_when_abi_syscall_constant_is_missing(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "constant"), "K_SYSCALL_UNKNOWN")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "missing_abi_syscall_constant", "syscalls.debug_heartbeat.constant")

    def test_fails_when_nop_syscall_constant_is_missing(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "nop", "constant"), "K_SYSCALL_UNKNOWN")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "missing_abi_syscall_constant", "syscalls.nop.constant")

    def test_fails_when_nop_payload_argument_is_not_null(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "nop", "payload_argument"), "heartbeat_payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_nop_payload_argument", "syscalls.nop.payload_argument")

    def test_fails_when_nop_return_status_is_wrong(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "nop", "success_behavior", "return_status"), "K_INVALID")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_nop_return_status", "syscalls.nop.success_behavior.return_status")

    def test_fails_when_nop_mutates_payload(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "nop", "success_behavior", "mutates_payload"), ["sequence"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "nop_mutates_payload", "syscalls.nop.success_behavior.mutates_payload")

    def test_fails_when_payload_layout_is_missing(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "payload_layout"), "future_payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "missing_payload_layout", "syscalls.debug_heartbeat.payload_layout")

    def test_fails_when_request_sentinel_mismatches_manifest(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "request", "sequence"), "0xBADFEED")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "request_sentinel_mismatch", "syscalls.debug_heartbeat.request.sequence")

    def test_fails_when_response_sentinel_mismatches_manifest(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "response", "status_bits"), "K_INVALID")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "response_sentinel_mismatch", "syscalls.debug_heartbeat.response.status_bits")

    def test_fails_when_invalid_behavior_uses_unknown_status(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "invalid_behavior", "null_payload"), "K_FUTURE")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "unknown_status_constant", "syscalls.debug_heartbeat.invalid_behavior.null_payload")

    def test_fails_when_mutable_field_is_unknown(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("syscalls", "debug_heartbeat", "success_behavior", "mutates_payload"), ["sequence", "timestamp", "future"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "unknown_mutable_field", "syscalls.debug_heartbeat.success_behavior.mutates_payload")

    def test_fails_when_kernel_payload_retention_is_enabled(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("ownership", "kernel_may_retain_payload"), True)
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "payload_retention_forbidden", "ownership.kernel_may_retain_payload")

    def test_fails_when_proof_ownership_references_unknown_validator(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("proof_ownership", "future_validator"), ["future_field"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "unknown_proof_validator", "proof_ownership.future_validator")

    def test_failure_diagnostic_names_contract_field(self):
        result = self.validate_boundary_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "return", "register"), "rcx")
        )

        self.assertEqual(result.status, "fail")
        self.assert_boundary_failure(result, "wrong_return_register", "calling_convention.return.register")

    def validate_boundary_contract(
        self,
        *,
        contract: dict[str, object] | None = None,
        contract_text: str | None = None,
        manifest: dict[str, object] | None = None,
        mutate_contract=None,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_boundary_fixture(root)
            contract_data = contract if contract is not None else self.valid_contract(paths)
            if mutate_contract is not None:
                mutate_contract(contract_data)
            if contract_text is None:
                paths["contract"].write_text(json.dumps(contract_data))
            else:
                paths["contract"].write_text(contract_text)
            paths["manifest"].write_text(json.dumps(manifest or self.valid_manifest()))
            original_contract_path = syscall_boundary_contract._CONTRACT_PATH
            original_manifest_path = syscall_boundary_contract._ABI_MANIFEST_PATH
            syscall_boundary_contract._CONTRACT_PATH = paths["contract"]
            syscall_boundary_contract._ABI_MANIFEST_PATH = paths["manifest"]
            try:
                return SyscallBoundaryContractValidator().validate({})
            finally:
                syscall_boundary_contract._CONTRACT_PATH = original_contract_path
                syscall_boundary_contract._ABI_MANIFEST_PATH = original_manifest_path

    def validate_with_paths(self, paths: dict[str, Path]):
        original_contract_path = syscall_boundary_contract._CONTRACT_PATH
        original_manifest_path = syscall_boundary_contract._ABI_MANIFEST_PATH
        syscall_boundary_contract._CONTRACT_PATH = paths["contract"]
        syscall_boundary_contract._ABI_MANIFEST_PATH = paths["manifest"]
        try:
            return SyscallBoundaryContractValidator().validate({})
        finally:
            syscall_boundary_contract._CONTRACT_PATH = original_contract_path
            syscall_boundary_contract._ABI_MANIFEST_PATH = original_manifest_path

    def assert_boundary_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_BOUNDARY_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)

    def write_boundary_fixture(self, root: Path) -> dict[str, Path]:
        paths = {
            "assembly": root / "syscall.asm",
            "contract": root / "syscall_boundary_contract.v0.json",
            "manifest": root / "kozo_abi_manifest.json",
        }
        paths["assembly"].write_text(self.valid_assembly())
        return paths

    def set_value(self, data: dict[str, object], path: tuple[str, ...], value: object) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def valid_assembly(self) -> str:
        return (
            "bits 64\n"
            "extern syscall_dispatch\n"
            "global syscall_entry\n"
            "section .text\n"
            "syscall_entry:\n"
            "    mov rax, rdi\n"
            "    mov rbx, rsi\n"
            "    mov rdi, rax\n"
            "    mov rsi, rbx\n"
            "    call syscall_dispatch\n"
            "    ret\n"
        )

    def valid_contract(self, paths: dict[str, Path]) -> dict[str, object]:
        return {
            "version": 0,
            "architecture": "x86_64",
            "entry": {
                "symbol": "syscall_entry",
                "assembly_path": str(paths["assembly"]),
                "dispatcher_symbol": "syscall_dispatch",
            },
            "calling_convention": {
                "syscall_id": {
                    "source": "rust",
                    "register": "rdi",
                    "type": "K_SYSCALL_ID",
                },
                "payload": {
                    "source": "rust",
                    "register": "rsi",
                    "type": "HeartbeatPayload*",
                    "nullable": False,
                },
                "return": {
                    "register": "rax",
                    "type": "K_STATUS",
                },
            },
            "syscalls": {
                "nop": {
                    "constant": "K_SYSCALL_NOP",
                    "payload_argument": "null",
                    "success_behavior": {
                        "return_status": "K_OK",
                        "mutates_payload": [],
                    },
                },
                "debug_heartbeat": {
                    "constant": "K_SYSCALL_DEBUG_HEARTBEAT",
                    "payload_layout": "heartbeat_payload",
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
                    "invalid_behavior": {
                        "null_payload": "K_INVALID",
                        "bad_sequence": "K_INVALID",
                    },
                    "success_behavior": {
                        "return_status": "K_OK",
                        "mutates_payload": ["sequence", "timestamp", "status_bits"],
                    },
                }
            },
            "ownership": {
                "payload_owner": "rust_caller",
                "kernel_may_mutate": ["sequence", "timestamp", "status_bits"],
                "kernel_may_retain_payload": False,
            },
            "proof_ownership": {
                "bridge_alignment": ["entry_symbol", "register_handoff", "dispatcher_handoff"],
                "runtime_trap_path": ["rust_request_payload", "extern_bridge_call", "rust_nop_null_payload"],
                "execution_proof": ["odin_branch", "kernel_mutations", "serial_observation"],
                "return_path_proof": ["rust_return_validation", "response_payload_contract"],
                "protocol_contract_alignment": ["syscall_constant_agreement"],
                "layout_parity": ["payload_layout_agreement"],
            },
        }

    def valid_manifest(self) -> dict[str, object]:
        return {
            "version": 0,
            "canonical_header": "contracts/kozo_abi.h",
            "generated_bindings": {
                "rust": "bindings/rust/kozo_abi.rs",
                "odin": "bindings/odin/kozo_abi.odin",
            },
            "constants": {
                "status": {
                    "K_OK": 0,
                    "K_INVALID": 1,
                    "K_DENIED": 2,
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


if __name__ == "__main__":
    unittest.main()
