from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import SYSCALL_BOUNDARY_CONFORMANCE_INVALID
from harness.validators_impl import syscall_boundary_conformance
from harness.validators_impl.syscall_boundary_conformance import SyscallBoundaryConformanceValidator

KOZO_NEGATIVE_COVERAGE = {
    "syscall_boundary_conformance": {
        "missing_assembly_entry_symbol": "test_fails_when_assembly_entry_symbol_is_missing",
        "wrong_dispatcher_symbol": "test_fails_when_dispatcher_symbol_is_wrong",
        "wrong_syscall_id_register": "test_fails_when_syscall_id_register_is_wrong",
        "wrong_payload_register": "test_fails_when_payload_register_is_wrong",
        "rust_extern_symbol_mismatch": "test_fails_when_rust_extern_symbol_mismatches_contract",
        "rust_wrong_syscall_constant": "test_fails_when_rust_live_path_uses_wrong_syscall_constant",
        "rust_request_sentinel_mismatch": "test_fails_when_rust_request_sentinel_mismatches_contract",
        "rust_response_validation_mismatch": "test_fails_when_rust_response_validation_mismatches_contract",
        "odin_dispatcher_symbol_mismatch": "test_fails_when_odin_dispatcher_symbol_mismatches_contract",
        "odin_wrong_syscall_constant": "test_fails_when_odin_branch_uses_wrong_syscall_constant",
        "odin_null_payload_invalid_return_mismatch": "test_fails_when_odin_null_payload_invalid_return_mismatches_contract",
        "odin_bad_sequence_invalid_return_mismatch": "test_fails_when_odin_bad_sequence_invalid_return_mismatches_contract",
        "odin_unknown_mutated_field": "test_fails_when_odin_mutates_unknown_payload_field",
        "odin_response_sentinel_mismatch": "test_fails_when_odin_response_sentinel_mismatches_contract",
        "odin_success_return_mismatch": "test_fails_when_odin_success_return_mismatches_contract",
        "unknown_proof_validator": "test_fails_when_proof_ownership_references_unknown_validator",
        "diagnostic_names_contract_field": "test_failure_diagnostic_names_contract_field",
    }
}


class SyscallBoundaryConformanceValidatorTests(unittest.TestCase):
    def test_passes_when_live_sources_match_boundary_contract(self):
        result = self.validate_syscall_boundary_conformance()

        self.assertEqual(result.status, "pass")

    def test_fails_when_assembly_entry_symbol_is_missing(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_assembly=lambda source: source.replace("syscall_entry:", "dead_syscall_entry:")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "missing_assembly_entry_symbol", "entry.symbol")

    def test_fails_when_dispatcher_symbol_is_wrong(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("entry", "dispatcher_symbol"), "wrong_dispatcher")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_dispatcher_symbol", "entry.dispatcher_symbol")

    def test_fails_when_syscall_id_register_is_wrong(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "syscall_id", "register"), "rax")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_syscall_id_register", "calling_convention.syscall_id.register")

    def test_fails_when_payload_register_is_wrong(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "payload", "register"), "rdx")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "wrong_payload_register", "calling_convention.payload.register")

    def test_fails_when_rust_extern_symbol_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_rust=lambda source: source.replace("fn syscall_entry(", "fn dead_syscall_entry(")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "rust_extern_symbol_mismatch", "entry.symbol")

    def test_fails_when_rust_live_path_uses_wrong_syscall_constant(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_rust=lambda source: source.replace(
                "abi::K_SYSCALL_DEBUG_HEARTBEAT;",
                "abi::K_SYSCALL_WRONG_HEARTBEAT;",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "rust_wrong_syscall_constant", "syscalls.debug_heartbeat.constant")

    def test_fails_when_rust_request_sentinel_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_rust=lambda source: source.replace("sequence: 0xCAFEFEED", "sequence: 0xBADFEED")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "rust_request_sentinel_mismatch", "syscalls.debug_heartbeat.request.sequence")

    def test_fails_when_rust_response_validation_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_rust=lambda source: source.replace(
                "if payload.status_bits != abi::K_OK",
                "if payload.status_bits != abi::K_INVALID",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "rust_response_validation_mismatch", "syscalls.debug_heartbeat.response.status_bits")

    def test_fails_when_odin_dispatcher_symbol_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace("syscall_dispatch :: proc", "dead_dispatch :: proc")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "odin_dispatcher_symbol_mismatch", "entry.dispatcher_symbol")

    def test_fails_when_odin_branch_uses_wrong_syscall_constant(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace(
                "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
                "case abi.K_SYSCALL_WRONG_HEARTBEAT:",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "odin_wrong_syscall_constant", "syscalls.debug_heartbeat.constant")

    def test_fails_when_odin_null_payload_invalid_return_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace(
                "if payload == nil {\n\t\t\treturn abi.K_INVALID",
                "if payload == nil {\n\t\t\treturn abi.K_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(
            result,
            "odin_null_payload_invalid_return_mismatch",
            "syscalls.debug_heartbeat.invalid_behavior.null_payload",
        )

    def test_fails_when_odin_bad_sequence_invalid_return_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace(
                "if payload.sequence != 0xCAFEFEED {\n\t\t\treturn abi.K_INVALID",
                "if payload.sequence != 0xCAFEFEED {\n\t\t\treturn abi.K_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(
            result,
            "odin_bad_sequence_invalid_return_mismatch",
            "syscalls.debug_heartbeat.invalid_behavior.bad_sequence",
        )

    def test_fails_when_odin_mutates_unknown_payload_field(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace(
                "\t\tpayload.status_bits = u32(abi.K_OK)",
                "\t\tpayload.status_bits = u32(abi.K_OK)\n\t\tpayload.future = 1",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "odin_unknown_mutated_field", "ownership.kernel_may_mutate")

    def test_fails_when_odin_response_sentinel_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace("payload.timestamp = 0xDEADBEEF", "payload.timestamp = 0xBADBEEF")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "odin_response_sentinel_mismatch", "syscalls.debug_heartbeat.response.timestamp")

    def test_fails_when_odin_success_return_mismatches_contract(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_odin=lambda source: source.replace("\t\treturn abi.K_OK\n\t}", "\t\treturn abi.K_INVALID\n\t}")
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "odin_success_return_mismatch", "syscalls.debug_heartbeat.success_behavior.return_status")

    def test_fails_when_proof_ownership_references_unknown_validator(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("proof_ownership", "future_validator"), ["future_field"])
        )

        self.assertEqual(result.status, "fail")
        self.assert_conformance_failure(result, "unknown_proof_validator", "proof_ownership.future_validator")

    def test_failure_diagnostic_names_contract_field(self):
        result = self.validate_syscall_boundary_conformance(
            mutate_contract=lambda contract: self.set_value(contract, ("calling_convention", "payload", "register"), "rdx")
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SYSCALL_BOUNDARY_CONFORMANCE_INVALID)
        self.assertEqual(result.meta["reason"], "wrong_payload_register")
        self.assertEqual(result.meta["contract_field"], "calling_convention.payload.register")

    def validate_syscall_boundary_conformance(
        self,
        mutate_contract=None,
        mutate_assembly=None,
        mutate_rust=None,
        mutate_odin=None,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            paths = self.write_fixture(root, mutate_contract, mutate_assembly, mutate_rust, mutate_odin)
            original_paths = self.patch_validator_paths(paths)
            try:
                return SyscallBoundaryConformanceValidator().validate({})
            finally:
                self.restore_validator_paths(original_paths)

    def write_fixture(
        self,
        root: Path,
        mutate_contract,
        mutate_assembly,
        mutate_rust,
        mutate_odin,
    ) -> dict[str, Path]:
        paths = self.fixture_paths(root)
        contract = self.boundary_contract(paths["assembly"])
        assembly = self.assembly_source()
        rust = self.rust_source()
        odin = self.odin_source()
        if mutate_contract is not None:
            mutate_contract(contract)
        if mutate_assembly is not None:
            assembly = mutate_assembly(assembly)
        if mutate_rust is not None:
            rust = mutate_rust(rust)
        if mutate_odin is not None:
            odin = mutate_odin(odin)
        paths["contract"].write_text(json.dumps(contract))
        paths["assembly"].write_text(assembly)
        paths["rust"].write_text(rust)
        paths["odin"].write_text(odin)
        return paths

    def fixture_paths(self, root: Path) -> dict[str, Path]:
        return {
            "contract": root / "syscall_boundary_contract.v0.json",
            "assembly": root / "syscall.asm",
            "rust": root / "main.rs",
            "odin": root / "main.odin",
        }

    def patch_validator_paths(self, paths: dict[str, Path]) -> dict[str, Path]:
        original = {
            "contract": syscall_boundary_conformance._CONTRACT_PATH,
            "rust": syscall_boundary_conformance._RUST_MAIN,
            "odin": syscall_boundary_conformance._ODIN_MAIN,
        }
        syscall_boundary_conformance._CONTRACT_PATH = paths["contract"]
        syscall_boundary_conformance._RUST_MAIN = paths["rust"]
        syscall_boundary_conformance._ODIN_MAIN = paths["odin"]
        return original

    def restore_validator_paths(self, paths: dict[str, Path]) -> None:
        syscall_boundary_conformance._CONTRACT_PATH = paths["contract"]
        syscall_boundary_conformance._RUST_MAIN = paths["rust"]
        syscall_boundary_conformance._ODIN_MAIN = paths["odin"]

    def boundary_contract(self, assembly_path: Path) -> dict:
        return copy.deepcopy(
            {
                "version": 0,
                "architecture": "x86_64",
                "entry": {
                    "symbol": "syscall_entry",
                    "assembly_path": str(assembly_path),
                    "dispatcher_symbol": "syscall_dispatch",
                },
                "calling_convention": {
                    "syscall_id": {"source": "rust", "register": "rdi", "type": "K_SYSCALL_ID"},
                    "payload": {"source": "rust", "register": "rsi", "type": "HeartbeatPayload*", "nullable": False},
                    "return": {"register": "rax", "type": "K_STATUS"},
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
                "proof_ownership": {
                    "bridge_alignment": ["entry_symbol", "register_handoff", "dispatcher_handoff"],
                    "runtime_trap_path": ["rust_request_payload", "extern_bridge_call", "rust_nop_null_payload"],
                    "execution_proof": ["odin_branch", "kernel_mutations", "serial_observation"],
                    "return_path_proof": ["rust_return_validation", "response_payload_contract"],
                    "protocol_contract_alignment": ["syscall_constant_agreement"],
                    "layout_parity": ["payload_layout_agreement"],
                },
            }
        )

    def assembly_source(self) -> str:
        return """global syscall_entry
extern syscall_dispatch

syscall_entry:
    push rbp
    mov rbp, rsp
    mov rax, rdi
    mov rbx, rsi
    mov rdi, rax
    mov rsi, rbx
    call syscall_dispatch
    pop rbp
    ret

dead_path:
    mov rax, rdi
"""

    def rust_source(self) -> str:
        return """unsafe extern "C" {
    fn syscall_entry(id: u64, payload: *mut abi::HeartbeatPayload) -> u64;
}

fn bridge_syscall(syscall: abi::K_SYSCALL_ID, payload: &mut abi::HeartbeatPayload) -> abi::K_STATUS {
    unsafe { syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload) as abi::K_STATUS }
}

fn heartbeat_request() {
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;
    let mut payload = abi::HeartbeatPayload {
        sequence: 0xCAFEFEED,
        timestamp: 0,
        status_bits: abi::K_INVALID,
    };
    let status = bridge_syscall(syscall, &mut payload);
    validate_heartbeat_return_path(status, &payload);
}

fn validate_heartbeat_return_path(status: abi::K_STATUS, payload: &abi::HeartbeatPayload) {
    if status != abi::K_OK {
        panic!("bad status");
    }
    if payload.sequence != 0xCAFEFEEE {
        panic!("bad sequence");
    }
    if payload.timestamp != 0xDEADBEEF {
        panic!("bad timestamp");
    }
    if payload.status_bits != abi::K_OK {
        panic!("bad status_bits");
    }
}
"""

    def odin_source(self) -> str:
        return """syscall_dispatch :: proc "c" (id: abi.K_SYSCALL_ID, payload: ^abi.Heartbeat_Payload) -> abi.K_STATUS {
	switch id {
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
        self.assertEqual(result.code, SYSCALL_BOUNDARY_CONFORMANCE_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


if __name__ == "__main__":
    unittest.main()
