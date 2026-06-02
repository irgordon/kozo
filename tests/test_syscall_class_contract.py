from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import SYSCALL_CLASS_CONTRACT_INVALID
from harness.validators_impl import syscall_class_contract
from harness.validators_impl.syscall_class_contract import SyscallClassContractValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_class_contract": {
        "missing_contract_file": "test_fails_when_contract_file_is_missing",
        "invalid_json": "test_fails_when_contract_json_is_invalid",
        "schema_violation": "test_fails_when_contract_schema_is_invalid",
        "missing_no_payload_status_class": "test_fails_when_no_payload_status_class_is_missing",
        "missing_payload_mutating_status_class": "test_fails_when_payload_mutating_status_class_is_missing",
        "malformed_no_payload_status": "test_fails_when_no_payload_status_semantics_are_malformed",
        "malformed_payload_mutating_status": "test_fails_when_payload_mutating_status_semantics_are_malformed",
        "unknown_example_syscall": "test_fails_when_class_example_references_unknown_syscall",
        "missing_syscall_class": "test_fails_when_syscall_table_entry_lacks_class",
        "unknown_syscall_class": "test_fails_when_syscall_table_entry_uses_unknown_class",
        "nop_wrong_class": "test_fails_when_nop_uses_payload_mutating_class",
        "status_wrong_class": "test_fails_when_status_uses_payload_mutating_class",
        "heartbeat_wrong_class": "test_fails_when_heartbeat_uses_no_payload_class",
        "kind_class_mismatch": "test_fails_when_kind_and_class_mismatch",
        "no_payload_has_layout": "test_fails_when_no_payload_syscall_has_payload_layout",
        "no_payload_has_request": "test_fails_when_no_payload_syscall_has_request",
        "no_payload_has_response": "test_fails_when_no_payload_syscall_has_response",
        "no_payload_mutates_payload": "test_fails_when_no_payload_syscall_allows_payload_mutation",
        "status_payload_layout_reference": "test_fails_when_status_syscall_has_payload_layout",
        "status_mutates_payload": "test_fails_when_status_declares_payload_mutation",
        "payload_missing_layout": "test_fails_when_payload_mutating_syscall_lacks_payload_layout",
        "payload_missing_request": "test_fails_when_payload_mutating_syscall_lacks_request",
        "payload_missing_response": "test_fails_when_payload_mutating_syscall_lacks_response",
        "payload_unknown_mutation_field": "test_fails_when_payload_mutating_syscall_mutates_unknown_field",
        "diagnostic_names_class_field": "test_failure_diagnostic_names_class_field",
    }
}


class SyscallClassContractValidatorTests(unittest.TestCase):
    def test_passes_when_classes_match_table_and_manifest(self):
        result = self.validate_syscall_class_contract()

        self.assertEqual(result.status, "pass")

    def test_fails_when_contract_file_is_missing(self):
        result = self.validate_syscall_class_contract(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_syscall_class_contract(contract_text="{")

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_invalid(self):
        result = self.validate_syscall_class_contract(contract={"version": 0})

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_no_payload_status_class_is_missing(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: contract["classes"].pop("no_payload_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "missing_no_payload_status_class", "classes.no_payload_status")

    def test_fails_when_payload_mutating_status_class_is_missing(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: contract["classes"].pop("payload_mutating_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "missing_payload_mutating_status_class", "classes.payload_mutating_status")

    def test_fails_when_no_payload_status_semantics_are_malformed(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("classes", "no_payload_status", "payload_argument"), "pointer")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "malformed_no_payload_status", "classes.no_payload_status.payload_argument")

    def test_fails_when_payload_mutating_status_semantics_are_malformed(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("classes", "payload_mutating_status", "mutates_payload"), "forbidden")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "malformed_payload_mutating_status", "classes.payload_mutating_status.mutates_payload")

    def test_fails_when_class_example_references_unknown_syscall(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("classes", "no_payload_status", "valid_examples"), ["future"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "unknown_example_syscall", "classes.no_payload_status.valid_examples")

    def test_fails_when_syscall_table_entry_lacks_class(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: table["valid_syscalls"]["nop"].pop("class")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "missing_syscall_class", "valid_syscalls.nop.class")

    def test_fails_when_syscall_table_entry_uses_unknown_class(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "class"), "future_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "unknown_syscall_class", "valid_syscalls.nop.class")

    def test_fails_when_nop_uses_payload_mutating_class(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "class"), "payload_mutating_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "nop_wrong_class", "valid_syscalls.nop.class")

    def test_fails_when_status_uses_payload_mutating_class(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "status", "class"), "payload_mutating_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "status_wrong_class", "valid_syscalls.status.class")

    def test_fails_when_heartbeat_uses_no_payload_class(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "debug_heartbeat", "class"), "no_payload_status")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "heartbeat_wrong_class", "valid_syscalls.debug_heartbeat.class")

    def test_fails_when_kind_and_class_mismatch(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "kind"), "payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "kind_class_mismatch", "valid_syscalls.nop.class")

    def test_fails_when_no_payload_syscall_has_payload_layout(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "payload_layout"), "heartbeat_payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_has_layout", "valid_syscalls.nop.payload_layout")

    def test_fails_when_no_payload_syscall_has_request(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "request"), {"sequence": "0xCAFEFEED"})
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_has_request", "valid_syscalls.nop.request")

    def test_fails_when_no_payload_syscall_has_response(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "response"), {"status_bits": "K_OK"})
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_has_response", "valid_syscalls.nop.response")

    def test_fails_when_no_payload_syscall_allows_payload_mutation(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "nop", "must_not_mutate_payload"), False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_mutates_payload", "valid_syscalls.nop.must_not_mutate_payload")

    def test_fails_when_status_syscall_has_payload_layout(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "status", "payload_layout"), "heartbeat_payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_has_layout", "valid_syscalls.status.payload_layout")

    def test_fails_when_status_declares_payload_mutation(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "status", "mutates_payload"), ["sequence"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "no_payload_mutates_payload", "valid_syscalls.status.mutates_payload")

    def test_fails_when_payload_mutating_syscall_lacks_payload_layout(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: table["valid_syscalls"]["debug_heartbeat"].pop("payload_layout")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "payload_missing_layout", "valid_syscalls.debug_heartbeat.payload_layout")

    def test_fails_when_payload_mutating_syscall_lacks_request(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: table["valid_syscalls"]["debug_heartbeat"].pop("request")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "payload_missing_request", "valid_syscalls.debug_heartbeat.request")

    def test_fails_when_payload_mutating_syscall_lacks_response(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: table["valid_syscalls"]["debug_heartbeat"].pop("response")
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "payload_missing_response", "valid_syscalls.debug_heartbeat.response")

    def test_fails_when_payload_mutating_syscall_mutates_unknown_field(self):
        result = self.validate_syscall_class_contract(
            mutate_table=lambda table: self.set_value(table, ("valid_syscalls", "debug_heartbeat", "mutates_payload"), ["future"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "payload_unknown_mutation_field", "valid_syscalls.debug_heartbeat.mutates_payload")

    def test_failure_diagnostic_names_class_field(self):
        result = self.validate_syscall_class_contract(
            mutate_contract=lambda contract: self.set_value(contract, ("classes", "no_payload_status", "request_required"), True)
        )

        self.assertEqual(result.status, "fail")
        self.assert_class_failure(result, "malformed_no_payload_status", "classes.no_payload_status.request_required")

    def validate_syscall_class_contract(
        self,
        mutate_contract=None,
        mutate_table=None,
        mutate_manifest=None,
        contract=None,
        contract_text=None,
        remove_contract=False,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_fixture(root, mutate_contract, mutate_table, mutate_manifest, contract, contract_text, remove_contract)
            original_paths = self.patch_validator_paths(paths)
            try:
                return SyscallClassContractValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(
        self,
        root: Path,
        mutate_contract,
        mutate_table,
        mutate_manifest,
        contract,
        contract_text,
        remove_contract,
    ) -> dict[str, Path]:
        paths = self.fixture_paths(root)
        contract_data = self.class_contract() if contract is None else contract
        table_data = self.table_contract()
        manifest_data = self.abi_manifest()
        if mutate_contract is not None:
            mutate_contract(contract_data)
        if mutate_table is not None:
            mutate_table(table_data)
        if mutate_manifest is not None:
            mutate_manifest(manifest_data)
        if not remove_contract:
            paths["contract"].write_text(contract_text if contract_text is not None else json.dumps(contract_data))
        paths["table"].write_text(json.dumps(table_data))
        paths["manifest"].write_text(json.dumps(manifest_data))
        return paths

    def fixture_paths(self, root: Path) -> dict[str, Path]:
        return {
            "contract": root / "syscall_class_contract.v0.json",
            "table": root / "syscall_table_contract.v0.json",
            "manifest": root / "kozo_abi_manifest.json",
        }

    def patch_validator_paths(self, paths: dict[str, Path]) -> dict[str, Path]:
        original = {
            "contract": syscall_class_contract._CONTRACT_PATH,
            "table": syscall_class_contract._TABLE_CONTRACT_PATH,
            "manifest": syscall_class_contract._ABI_MANIFEST_PATH,
        }
        syscall_class_contract._CONTRACT_PATH = paths["contract"]
        syscall_class_contract._TABLE_CONTRACT_PATH = paths["table"]
        syscall_class_contract._ABI_MANIFEST_PATH = paths["manifest"]
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        syscall_class_contract._CONTRACT_PATH = paths["contract"]
        syscall_class_contract._TABLE_CONTRACT_PATH = paths["table"]
        syscall_class_contract._ABI_MANIFEST_PATH = paths["manifest"]

    def class_contract(self) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "classes": {
                    "no_payload_status": {
                        "payload_argument": "null",
                        "payload_layout_required": False,
                        "request_required": False,
                        "response_required": False,
                        "mutates_payload": "forbidden",
                        "return_status_required": True,
                        "valid_examples": ["nop", "status"],
                    },
                    "payload_mutating_status": {
                        "payload_argument": "pointer",
                        "payload_layout_required": True,
                        "request_required": True,
                        "response_required": True,
                        "mutates_payload": "required",
                        "return_status_required": True,
                        "invalid_behavior_required": ["null_payload", "bad_sequence"],
                        "valid_examples": ["debug_heartbeat"],
                    },
                },
            }
        )

    def table_contract(self) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "architecture": "x86_64",
                "dispatcher": {
                    "symbol": "syscall_dispatch",
                    "source_path": "kernel/main.odin",
                    "syscall_id_type": "K_SYSCALL_ID",
                    "return_type": "K_STATUS",
                },
                "valid_syscalls": {
                    "nop": {
                        "kind": "no_payload",
                        "class": "no_payload_status",
                        "constant": "K_SYSCALL_NOP",
                        "branch_selector": "abi.K_SYSCALL_NOP",
                        "payload_argument": "null",
                        "return_status": "K_OK",
                        "mutates_payload": [],
                        "must_not_mutate_payload": True,
                    },
                    "status": {
                        "kind": "no_payload",
                        "class": "no_payload_status",
                        "constant": "K_SYSCALL_STATUS",
                        "branch_selector": "abi.K_SYSCALL_STATUS",
                        "payload_argument": "null",
                        "return_status": "K_OK",
                        "mutates_payload": [],
                        "must_not_mutate_payload": True,
                    },
                    "debug_heartbeat": {
                        "kind": "payload",
                        "class": "payload_mutating_status",
                        "constant": "K_SYSCALL_DEBUG_HEARTBEAT",
                        "payload_layout": "heartbeat_payload",
                        "branch_selector": "abi.K_SYSCALL_DEBUG_HEARTBEAT",
                        "boundary_contract": "debug_heartbeat",
                        "return_status": "K_OK",
                        "request": {"sequence": "0xCAFEFEED", "timestamp": 0, "status_bits": "K_INVALID"},
                        "response": {"sequence": "0xCAFEFEEE", "timestamp": "0xDEADBEEF", "status_bits": "K_OK"},
                        "invalid_behavior": {"null_payload": "K_INVALID", "bad_sequence": "K_INVALID"},
                        "mutates_payload": ["sequence", "timestamp", "status_bits"],
                    },
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

    def abi_manifest(self) -> dict:
        return {
            "version": 0,
            "canonical_header": "contracts/kozo_abi.h",
            "generated_bindings": {
                "rust": "bindings/rust/kozo_abi.rs",
                "odin": "bindings/odin/kozo_abi.odin",
            },
            "constants": {
                "status": {"K_OK": 0, "K_INVALID": 1, "K_DENIED": 2},
                "syscalls": {"K_SYSCALL_NOP": 0, "K_SYSCALL_DEBUG_HEARTBEAT": 1, "K_SYSCALL_STATUS": 2},
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

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_class_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_CLASS_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
