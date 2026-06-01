from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import SYSCALL_TABLE_CONFORMANCE_INVALID
from harness.validators_impl import syscall_table_conformance
from harness.validators_impl.syscall_table_conformance import SyscallTableConformanceValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_table_conformance": {
        "missing_dispatcher_source": "test_fails_when_dispatcher_source_is_missing",
        "missing_dispatcher_symbol": "test_fails_when_dispatcher_symbol_is_missing",
        "syscall_id_type_mismatch": "test_fails_when_dispatcher_syscall_id_type_mismatches",
        "return_type_mismatch": "test_fails_when_dispatcher_return_type_mismatches",
        "missing_valid_syscall_branch": "test_fails_when_valid_syscall_branch_is_missing",
        "hardcoded_branch_selector": "test_fails_when_branch_selector_is_hardcoded_numeric",
        "wrong_branch_body": "test_fails_when_branch_selector_maps_to_wrong_body",
        "extra_uncontracted_branch": "test_fails_when_extra_handled_branch_is_not_contract_allowed",
        "payload_layout_mismatch": "test_fails_when_payload_layout_type_mismatches",
        "missing_unknown_branch": "test_fails_when_unknown_default_branch_is_missing",
        "wrong_unknown_return_status": "test_fails_when_unknown_default_return_status_mismatches",
        "unknown_path_mutates_payload": "test_fails_when_unknown_default_path_mutates_payload",
        "unknown_path_calls_heartbeat_logic": "test_fails_when_unknown_default_path_calls_heartbeat_logic",
        "unknown_path_unreachable": "test_fails_when_unknown_default_path_is_unreachable",
        "missing_abi_syscall_constant": "test_fails_when_abi_manifest_is_missing_syscall_constant",
        "missing_abi_payload_layout": "test_fails_when_payload_layout_reference_is_missing_from_abi_manifest",
        "missing_nop_branch": "test_fails_when_nop_branch_is_missing",
        "nop_hardcoded_selector": "test_fails_when_nop_branch_selector_is_hardcoded_numeric",
        "wrong_nop_return_status": "test_fails_when_nop_return_status_mismatches",
        "nop_mutates_payload": "test_fails_when_nop_branch_mutates_payload",
        "nop_uses_payload_layout": "test_fails_when_nop_branch_uses_heartbeat_payload_layout",
        "missing_nop_abi_constant": "test_fails_when_nop_abi_constant_is_missing",
        "diagnostic_names_contract_field": "test_failure_diagnostic_names_contract_field",
    }
}


class SyscallTableConformanceValidatorTests(unittest.TestCase):
    def test_passes_when_live_dispatcher_conforms_to_table_contract(self):
        result = self.validate_syscall_table_conformance()

        self.assertEqual(result.status, "pass")

    def test_fails_when_dispatcher_source_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("dispatcher", "source_path"), "/missing/main.odin")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_dispatcher_source", "dispatcher.source_path")

    def test_fails_when_dispatcher_symbol_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("syscall_dispatch :: proc", "dead_dispatch :: proc")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_dispatcher_symbol", "dispatcher.symbol")

    def test_fails_when_dispatcher_syscall_id_type_mismatches(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("id: abi.K_SYSCALL_ID", "id: abi.K_STATUS")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "syscall_id_type_mismatch", "dispatcher.syscall_id_type")

    def test_fails_when_dispatcher_return_type_mismatches(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("-> abi.K_STATUS", "-> abi.K_SYSCALL_ID")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "return_type_mismatch", "dispatcher.return_type")

    def test_fails_when_valid_syscall_branch_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("case abi.K_SYSCALL_DEBUG_HEARTBEAT:", "case abi.K_SYSCALL_MISSING:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_valid_syscall_branch", "valid_syscalls.debug_heartbeat.branch_selector")

    def test_fails_when_branch_selector_is_hardcoded_numeric(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("case abi.K_SYSCALL_DEBUG_HEARTBEAT:", "case 1:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "hardcoded_branch_selector", "valid_syscalls.debug_heartbeat.branch_selector")

    def test_fails_when_branch_selector_maps_to_wrong_body(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("payload.status_bits = u32(abi.K_OK)", "payload.status_bits = u32(abi.K_INVALID)")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_branch_body", "valid_syscalls.debug_heartbeat.branch_selector")

    def test_fails_when_extra_handled_branch_is_not_contract_allowed(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
                "case abi.K_DENIED:\n\t\treturn abi.K_DENIED\n\tcase abi.K_SYSCALL_DEBUG_HEARTBEAT:",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "extra_uncontracted_branch", "valid_syscalls")

    def test_fails_when_payload_layout_type_mismatches(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("payload: ^abi.Heartbeat_Payload", "payload: ^abi.Future_Payload")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "payload_layout_mismatch", "valid_syscalls.debug_heartbeat.payload_layout")

    def test_fails_when_unknown_default_branch_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("\treturn abi.K_INVALID\n}", "}")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_unknown_branch", "unknown_syscall_behavior.return_status")

    def test_fails_when_unknown_default_return_status_mismatches(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("\treturn abi.K_INVALID\n}", "\treturn abi.K_OK\n}")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_unknown_return_status", "unknown_syscall_behavior.return_status")

    def test_fails_when_unknown_default_path_mutates_payload(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "\treturn abi.K_INVALID\n}",
                "\tpayload.sequence = 0\n\treturn abi.K_INVALID\n}",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "unknown_path_mutates_payload", "unknown_syscall_behavior.must_not_mutate_payload")

    def test_fails_when_unknown_default_path_calls_heartbeat_logic(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "\treturn abi.K_INVALID\n}",
                "\tx86_64.serial_log_debug_heartbeat_recv(0)\n\treturn abi.K_INVALID\n}",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "unknown_path_calls_heartbeat_logic", "unknown_syscall_behavior")

    def test_fails_when_unknown_default_path_is_unreachable(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "\treturn abi.K_INVALID\n}",
                "\tunreachable()\n\treturn abi.K_INVALID\n}",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "unknown_path_unreachable", "unknown_syscall_behavior.return_status")

    def test_fails_when_abi_manifest_is_missing_syscall_constant(self):
        result = self.validate_syscall_table_conformance(
            mutate_manifest=lambda manifest: manifest["constants"]["syscalls"].pop("K_SYSCALL_DEBUG_HEARTBEAT")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_abi_syscall_constant", "valid_syscalls.debug_heartbeat.constant")

    def test_fails_when_payload_layout_reference_is_missing_from_abi_manifest(self):
        result = self.validate_syscall_table_conformance(
            mutate_contract=lambda contract: self.set_value(
                contract,
                ("valid_syscalls", "debug_heartbeat", "payload_layout"),
                "future_payload",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_abi_payload_layout", "valid_syscalls.debug_heartbeat.payload_layout")

    def test_fails_when_nop_branch_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("case abi.K_SYSCALL_NOP:", "case abi.K_SYSCALL_NOP_DISABLED:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_valid_syscall_branch", "valid_syscalls.nop.branch_selector")

    def test_fails_when_nop_branch_selector_is_hardcoded_numeric(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("case abi.K_SYSCALL_NOP:", "case 0:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "hardcoded_branch_selector", "valid_syscalls.nop.branch_selector")

    def test_fails_when_nop_return_status_mismatches(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "case abi.K_SYSCALL_NOP:\n\t\treturn abi.K_OK",
                "case abi.K_SYSCALL_NOP:\n\t\treturn abi.K_INVALID",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_no_payload_return_status", "valid_syscalls.nop.return_status")

    def test_fails_when_nop_branch_mutates_payload(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "case abi.K_SYSCALL_NOP:\n\t\treturn abi.K_OK",
                "case abi.K_SYSCALL_NOP:\n\t\tpayload.sequence = 0\n\t\treturn abi.K_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "no_payload_mutates_payload", "valid_syscalls.nop.must_not_mutate_payload")

    def test_fails_when_nop_branch_uses_heartbeat_payload_layout(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace(
                "case abi.K_SYSCALL_NOP:\n\t\treturn abi.K_OK",
                "case abi.K_SYSCALL_NOP:\n\t\tif payload != nil {}\n\t\treturn abi.K_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "no_payload_uses_payload_layout", "valid_syscalls.nop")

    def test_fails_when_nop_abi_constant_is_missing(self):
        result = self.validate_syscall_table_conformance(
            mutate_manifest=lambda manifest: manifest["constants"]["syscalls"].pop("K_SYSCALL_NOP")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_abi_syscall_constant", "valid_syscalls.nop.constant")

    def test_failure_diagnostic_names_contract_field(self):
        result = self.validate_syscall_table_conformance(
            mutate_dispatcher=lambda source: source.replace("-> abi.K_STATUS", "-> abi.K_SYSCALL_ID")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_TABLE_CONFORMANCE_INVALID)
        self.assertEqual(result.meta["reason"], "return_type_mismatch")
        self.assertEqual(result.meta["contract_field"], "dispatcher.return_type")

    def validate_syscall_table_conformance(
        self,
        mutate_contract=None,
        mutate_manifest=None,
        mutate_dispatcher=None,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_fixture(root, mutate_contract, mutate_manifest, mutate_dispatcher)
            original_paths = self.patch_validator_paths(paths)
            try:
                return SyscallTableConformanceValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(
        self,
        root: Path,
        mutate_contract,
        mutate_manifest,
        mutate_dispatcher,
    ) -> dict[str, Path]:
        paths = self.fixture_paths(root)
        contract = self.table_contract(paths)
        manifest = self.abi_manifest()
        dispatcher = self.dispatcher_source()
        if mutate_contract is not None:
            mutate_contract(contract)
        if mutate_manifest is not None:
            mutate_manifest(manifest)
        if mutate_dispatcher is not None:
            dispatcher = mutate_dispatcher(dispatcher)
        paths["contract"].write_text(json.dumps(contract))
        paths["manifest"].write_text(json.dumps(manifest))
        paths["dispatcher"].write_text(dispatcher)
        return paths

    def fixture_paths(self, root: Path) -> dict[str, Path]:
        return {
            "contract": root / "syscall_table_contract.v0.json",
            "manifest": root / "kozo_abi_manifest.json",
            "dispatcher": root / "main.odin",
        }

    def patch_validator_paths(self, paths: dict[str, Path]) -> dict[str, Path]:
        original = {
            "contract": syscall_table_conformance._CONTRACT_PATH,
            "manifest": syscall_table_conformance._ABI_MANIFEST_PATH,
        }
        syscall_table_conformance._CONTRACT_PATH = paths["contract"]
        syscall_table_conformance._ABI_MANIFEST_PATH = paths["manifest"]
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        syscall_table_conformance._CONTRACT_PATH = paths["contract"]
        syscall_table_conformance._ABI_MANIFEST_PATH = paths["manifest"]

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
                    "nop": {
                        "kind": "no_payload",
                        "constant": "K_SYSCALL_NOP",
                        "branch_selector": "abi.K_SYSCALL_NOP",
                        "return_status": "K_OK",
                        "must_not_mutate_payload": True,
                    },
                    "debug_heartbeat": {
                        "kind": "payload",
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

    def abi_manifest(self) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "canonical_header": "contracts/kozo_abi.h",
                "generated_bindings": {
                    "rust": "bindings/rust/kozo_abi.rs",
                    "odin": "bindings/odin/kozo_abi.odin",
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

    def set_value(self, data: dict, path: tuple[str, ...], value) -> None:
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    def assert_conformance_failure(self, result, reason: str, contract_field: str) -> None:
        self.assertEqual(result.code, SYSCALL_TABLE_CONFORMANCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
