from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import SYSCALL_TABLE_CONTRACT_INVALID
from harness.validators_impl import syscall_table_contract
from harness.validators_impl.syscall_table_contract import SyscallTableContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_table_contract": {
        "missing_contract_file": "test_fails_when_contract_file_is_missing",
        "invalid_json": "test_fails_when_contract_json_is_invalid",
        "schema_violation": "test_fails_when_contract_schema_is_invalid",
        "wrong_architecture": "test_fails_when_architecture_is_wrong",
        "missing_dispatcher_source": "test_fails_when_dispatcher_source_is_missing",
        "wrong_dispatcher_symbol": "test_fails_when_dispatcher_symbol_is_wrong",
        "missing_abi_syscall_constant": "test_fails_when_syscall_constant_is_missing_from_manifest",
        "missing_payload_layout": "test_fails_when_payload_layout_is_missing_from_manifest",
        "missing_branch_selector": "test_fails_when_branch_selector_is_missing_from_dispatcher",
        "wrong_branch_mapping": "test_fails_when_syscall_constant_maps_to_wrong_branch",
        "missing_unknown_syscall_branch": "test_fails_when_unknown_syscall_branch_is_missing",
        "wrong_unknown_syscall_return": "test_fails_when_unknown_syscall_returns_wrong_status",
        "unknown_path_mutates_payload": "test_fails_when_unknown_syscall_path_mutates_payload",
        "diagnostic_names_contract_field": "test_failure_diagnostic_names_contract_field",
    }
}


class SyscallTableContractValidatorTests(unittest.TestCase):
    def test_passes_when_contract_matches_manifest_boundary_and_dispatcher(self):
        result = self.validate_syscall_table_contract()

        self.assertEqual(result.status, "pass")

    def test_fails_when_contract_file_is_missing(self):
        result = self.validate_syscall_table_contract(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_syscall_table_contract(contract_text="{")

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_invalid(self):
        result = self.validate_syscall_table_contract(contract={"version": 0})

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_architecture_is_wrong(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("architecture",), "aarch64")
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "wrong_architecture", "architecture")

    def test_fails_when_dispatcher_source_is_missing(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("dispatcher", "source_path"), "/missing/kernel.odin")
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_dispatcher_source", "dispatcher.source_path")

    def test_fails_when_dispatcher_symbol_is_wrong(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("dispatcher", "symbol"), "wrong_dispatch")
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "wrong_dispatcher_symbol", "dispatcher.symbol")

    def test_fails_when_syscall_constant_is_missing_from_manifest(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(
                contract,
                ("valid_syscalls", "debug_heartbeat", "constant"),
                "K_SYSCALL_UNKNOWN",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_abi_syscall_constant", "valid_syscalls.debug_heartbeat.constant")

    def test_fails_when_payload_layout_is_missing_from_manifest(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(
                contract,
                ("valid_syscalls", "debug_heartbeat", "payload_layout"),
                "future_payload",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_payload_layout", "valid_syscalls.debug_heartbeat.payload_layout")

    def test_fails_when_branch_selector_is_missing_from_dispatcher(self):
        result = self.validate_syscall_table_contract(
            mutate_dispatcher=lambda source: source.replace(
                "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
                "case abi.K_SYSCALL_MISSING_HEARTBEAT:",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_branch_selector", "valid_syscalls.debug_heartbeat.branch_selector")

    def test_fails_when_syscall_constant_maps_to_wrong_branch(self):
        result = self.validate_syscall_table_contract(
            mutate_dispatcher=lambda source: source.replace(
                "if payload.sequence != 0xCAFEFEED {",
                "if false {",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "wrong_branch_mapping", "valid_syscalls.debug_heartbeat.branch_selector")

    def test_fails_when_unknown_syscall_branch_is_missing(self):
        result = self.validate_syscall_table_contract(
            mutate_dispatcher=lambda source: source.replace("\treturn abi.K_INVALID\n}", "}")
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "missing_unknown_syscall_branch", "unknown_syscall_behavior.return_status")

    def test_fails_when_unknown_syscall_returns_wrong_status(self):
        result = self.validate_syscall_table_contract(
            mutate_dispatcher=lambda source: source.replace("\treturn abi.K_INVALID\n}", "\treturn abi.K_OK\n}")
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "wrong_unknown_syscall_return", "unknown_syscall_behavior.return_status")

    def test_fails_when_unknown_syscall_path_mutates_payload(self):
        result = self.validate_syscall_table_contract(
            mutate_dispatcher=lambda source: source.replace(
                "\treturn abi.K_INVALID\n}",
                "\tpayload.sequence = 0\n\treturn abi.K_INVALID\n}",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_table_failure(result, "unknown_path_mutates_payload", "unknown_syscall_behavior.must_not_mutate_payload")

    def test_failure_diagnostic_names_contract_field(self):
        result = self.validate_syscall_table_contract(
            mutate_contract=lambda contract: self.set_value(
                contract,
                ("unknown_syscall_behavior", "return_status"),
                "K_DENIED",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_TABLE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], "wrong_unknown_syscall_return")
        self.assertEqual(result.meta["contract_field"], "unknown_syscall_behavior.return_status")

    def validate_syscall_table_contract(
        self,
        mutate_contract=None,
        mutate_manifest=None,
        mutate_boundary=None,
        mutate_dispatcher=None,
        contract=None,
        contract_text=None,
        remove_contract=False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_fixture(
                root,
                mutate_contract,
                mutate_manifest,
                mutate_boundary,
                mutate_dispatcher,
                contract,
                contract_text,
                remove_contract,
            )
            original_paths = self.patch_validator_paths(paths)
            try:
                return SyscallTableContractValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(
        self,
        root: Path,
        mutate_contract,
        mutate_manifest,
        mutate_boundary,
        mutate_dispatcher,
        contract,
        contract_text,
        remove_contract,
    ) -> dict[str, Path]:
        paths = self.fixture_paths(root)
        contract_data = self.table_contract(paths)
        manifest_data = self.abi_manifest(paths)
        boundary_data = self.boundary_contract()
        dispatcher_source = self.dispatcher_source()
        if contract is not None:
            contract_data = contract
        if mutate_contract is not None:
            mutate_contract(contract_data)
        if mutate_manifest is not None:
            mutate_manifest(manifest_data)
        if mutate_boundary is not None:
            mutate_boundary(boundary_data)
        if mutate_dispatcher is not None:
            dispatcher_source = mutate_dispatcher(dispatcher_source)
        self.write_json_or_text(paths["contract"], contract_data, contract_text, remove_contract)
        paths["manifest"].write_text(json.dumps(manifest_data))
        paths["boundary"].write_text(json.dumps(boundary_data))
        paths["dispatcher"].write_text(dispatcher_source)
        paths["rust_binding"].write_text(self.rust_binding_source())
        paths["odin_binding"].write_text(self.odin_binding_source())
        return paths

    def write_json_or_text(self, path: Path, data: dict, text: str | None, remove: bool) -> None:
        if remove:
            return
        if text is not None:
            path.write_text(text)
            return
        path.write_text(json.dumps(data))

    def fixture_paths(self, root: Path) -> dict[str, Path]:
        return {
            "contract": root / "syscall_table_contract.v0.json",
            "manifest": root / "kozo_abi_manifest.json",
            "boundary": root / "syscall_boundary_contract.v0.json",
            "dispatcher": root / "main.odin",
            "rust_binding": root / "kozo_abi.rs",
            "odin_binding": root / "kozo_abi.odin",
        }

    def patch_validator_paths(self, paths: dict[str, Path]) -> dict[str, Path]:
        original = {
            "contract": syscall_table_contract._CONTRACT_PATH,
            "manifest": syscall_table_contract._ABI_MANIFEST_PATH,
            "boundary": syscall_table_contract._BOUNDARY_CONTRACT_PATH,
        }
        syscall_table_contract._CONTRACT_PATH = paths["contract"]
        syscall_table_contract._ABI_MANIFEST_PATH = paths["manifest"]
        syscall_table_contract._BOUNDARY_CONTRACT_PATH = paths["boundary"]
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        syscall_table_contract._CONTRACT_PATH = paths["contract"]
        syscall_table_contract._ABI_MANIFEST_PATH = paths["manifest"]
        syscall_table_contract._BOUNDARY_CONTRACT_PATH = paths["boundary"]

    def table_contract(self, paths: dict[str, Path]) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "architecture": "x86_64",
                "dispatcher": {
                    "symbol": "syscall_dispatch",
                    "source_path": str(paths["dispatcher"]),
                    "syscall_id_type": "K_SYSCALL_ID",
                    "return_type": "K_STATUS",
                },
                "valid_syscalls": {
                    "debug_heartbeat": {
                        "constant": "K_SYSCALL_DEBUG_HEARTBEAT",
                        "payload_layout": "heartbeat_payload",
                        "branch_selector": "abi.K_SYSCALL_DEBUG_HEARTBEAT",
                        "boundary_contract": "debug_heartbeat",
                    }
                },
                "unknown_syscall_behavior": {
                    "return_status": "K_INVALID",
                    "must_not_mutate_payload": True,
                },
                "relationships": {
                    "abi_manifest": "contracts/kozo_abi_manifest.json",
                    "syscall_boundary_contract": "contracts/syscall_boundary_contract.v0.json",
                },
            }
        )

    def abi_manifest(self, paths: dict[str, Path]) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "canonical_header": "contracts/kozo_abi.h",
                "generated_bindings": {
                    "rust": str(paths["rust_binding"]),
                    "odin": str(paths["odin_binding"]),
                },
                "constants": {
                    "status": {"K_OK": 0, "K_INVALID": 1, "K_DENIED": 2},
                    "syscalls": {"K_SYSCALL_NOP": 0, "K_SYSCALL_DEBUG_HEARTBEAT": 1},
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
                    "request": {"sequence": "0xCAFEFEED", "timestamp": 0, "status_bits": "K_INVALID"},
                    "response": {"sequence": "0xCAFEFEEE", "timestamp": "0xDEADBEEF", "status_bits": "K_OK"},
                },
            }
        )

    def boundary_contract(self) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "architecture": "x86_64",
                "entry": {
                    "symbol": "syscall_entry",
                    "assembly_path": "kernel/arch/x86_64/syscall.asm",
                    "dispatcher_symbol": "syscall_dispatch",
                },
                "calling_convention": {
                    "syscall_id": {"source": "rust", "register": "rdi", "type": "K_SYSCALL_ID"},
                    "payload": {"source": "rust", "register": "rsi", "type": "HeartbeatPayload*", "nullable": False},
                    "return": {"register": "rax", "type": "K_STATUS"},
                },
                "syscalls": {
                    "debug_heartbeat": {
                        "constant": "K_SYSCALL_DEBUG_HEARTBEAT",
                        "payload_layout": "heartbeat_payload",
                        "request": {"sequence": "0xCAFEFEED", "timestamp": 0, "status_bits": "K_INVALID"},
                        "response": {"sequence": "0xCAFEFEEE", "timestamp": "0xDEADBEEF", "status_bits": "K_OK"},
                        "invalid_behavior": {"null_payload": "K_INVALID", "bad_sequence": "K_INVALID"},
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
                "proof_ownership": {},
            }
        )

    def dispatcher_source(self) -> str:
        return """syscall_dispatch :: proc "c" (
	id: abi.K_SYSCALL_ID,
	payload: ^abi.Heartbeat_Payload,
) -> abi.K_STATUS {
	switch id {
	case abi.K_SYSCALL_NOP:
		return abi.K_OK
	case abi.K_SYSCALL_DEBUG_HEARTBEAT:
		if payload == nil {
			return abi.K_INVALID
		}
		if payload.sequence != 0xCAFEFEED {
			return abi.K_INVALID
		}
		payload.sequence = 0xCAFEFEEE
		payload.timestamp = 0xDEADBEEF
		payload.status_bits = u32(abi.K_OK)
		return abi.K_OK
	}
	return abi.K_INVALID
}
"""

    def rust_binding_source(self) -> str:
        return """pub type K_STATUS = u32;
pub type K_SYSCALL_ID = u32;
pub const K_INVALID: K_STATUS = 1;
pub const K_SYSCALL_DEBUG_HEARTBEAT: K_SYSCALL_ID = 1;
"""

    def odin_binding_source(self) -> str:
        return """K_STATUS :: u32
K_SYSCALL_ID :: u32
K_INVALID : K_STATUS : 1
K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1
"""

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_table_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.code, SYSCALL_TABLE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
