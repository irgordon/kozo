from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest, syscall_boundary_contract
from harness.codes import OK, SYSCALL_BOUNDARY_CONTRACT_INVALID
from harness.registry import CHECKS
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = syscall_boundary_contract.CONTRACT_PATH
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH

_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_ENTRY_SYMBOL = "syscall_entry"
_EXPECTED_DISPATCHER_SYMBOL = "syscall_dispatch"
_EXPECTED_SYSCALL_ID_REGISTER = "rdi"
_EXPECTED_PAYLOAD_REGISTER = "rsi"
_EXPECTED_RETURN_REGISTER = "rax"
_EXPECTED_SYSCALL_ID_TYPE = "K_SYSCALL_ID"
_EXPECTED_PAYLOAD_TYPE = "HeartbeatPayload*"
_EXPECTED_RETURN_TYPE = "K_STATUS"
_EXPECTED_PAYLOAD_OWNER = "rust_caller"


@dataclass(frozen=True)
class BoundaryIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class BoundaryContext:
    contract: syscall_boundary_contract.SyscallBoundaryContract
    manifest: abi_manifest.AbiManifest


class SyscallBoundaryContractValidator(BaseValidator):
    name = "syscall_boundary_contract"
    subsystem = "syscall_boundary_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _boundary_contract_issue(_CONTRACT_PATH, _ABI_MANIFEST_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Syscall boundary contract v0 matches the currently proven heartbeat trap path",
        )


def _boundary_contract_issue(contract_path: Path, manifest_path: Path) -> BoundaryIssue | None:
    context = _load_boundary_context(contract_path, manifest_path)
    if isinstance(context, BoundaryIssue):
        return context
    return _first_issue(
        _architecture_issue(context.contract),
        _entry_issue(context.contract),
        _calling_convention_issue(context.contract),
        _nop_syscall_issue(context),
        _heartbeat_syscall_issue(context),
        _invalid_behavior_issue(context),
        _success_behavior_issue(context),
        _ownership_issue(context),
        _proof_ownership_issue(context.contract),
    )


def _load_boundary_context(
    contract_path: Path,
    manifest_path: Path,
) -> BoundaryContext | BoundaryIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, BoundaryIssue):
        return contract
    manifest = _load_manifest(manifest_path)
    if isinstance(manifest, BoundaryIssue):
        return manifest
    return BoundaryContext(contract, manifest)


def _load_contract(path: Path) -> syscall_boundary_contract.SyscallBoundaryContract | BoundaryIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Syscall boundary contract is missing: {path}")
    data = _load_contract_data(path)
    if isinstance(data, BoundaryIssue):
        return data
    return _parse_contract(data)


def _load_contract_data(path: Path) -> dict | BoundaryIssue:
    try:
        return syscall_boundary_contract.load_contract_json(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Syscall boundary contract is invalid JSON: {exc}")


def _parse_contract(data: dict) -> syscall_boundary_contract.SyscallBoundaryContract | BoundaryIssue:
    try:
        syscall_boundary_contract.validate_contract_shape(data)
        return syscall_boundary_contract.parse_syscall_boundary_contract(data)
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Syscall boundary contract schema violation: {exc}")


def _load_manifest(path: Path) -> abi_manifest.AbiManifest | BoundaryIssue:
    try:
        return abi_manifest.load_abi_manifest(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("abi_manifest_unavailable", "abi_manifest", f"ABI manifest could not be loaded: {exc}")


def _architecture_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    if contract.architecture == _EXPECTED_ARCHITECTURE:
        return None
    return _issue("wrong_architecture", "architecture", f"Expected {_EXPECTED_ARCHITECTURE}, got {contract.architecture}")


def _entry_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    return _first_issue(
        _entry_symbol_issue(contract),
        _dispatcher_symbol_issue(contract),
        _assembly_path_issue(contract),
    )


def _entry_symbol_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    if contract.entry.symbol == _EXPECTED_ENTRY_SYMBOL:
        return None
    return _issue("wrong_entry_symbol", "entry.symbol", f"Expected {_EXPECTED_ENTRY_SYMBOL}, got {contract.entry.symbol}")


def _dispatcher_symbol_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    if contract.entry.dispatcher_symbol == _EXPECTED_DISPATCHER_SYMBOL:
        return None
    return _issue("wrong_dispatcher_symbol", "entry.dispatcher_symbol", f"Expected {_EXPECTED_DISPATCHER_SYMBOL}, got {contract.entry.dispatcher_symbol}")


def _assembly_path_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    assembly_path = syscall_boundary_contract.contract_repo_path(contract.entry.assembly_path)
    if not assembly_path.is_file():
        return _issue("missing_assembly_path", "entry.assembly_path", f"Assembly path does not exist: {contract.entry.assembly_path}")
    assembly_source = assembly_path.read_text()
    return _assembly_symbol_issue(contract, assembly_source)


def _assembly_symbol_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
    assembly_source: str,
) -> BoundaryIssue | None:
    if _assembly_exports_symbol(assembly_source, contract.entry.symbol) and _assembly_defines_label(assembly_source, contract.entry.symbol):
        return None
    return _issue("entry_symbol_not_in_assembly", "entry.symbol", f"Assembly does not export and define {contract.entry.symbol}")


def _calling_convention_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    convention = contract.calling_convention
    return _first_issue(
        _expected_value_issue(convention.syscall_id.register, _EXPECTED_SYSCALL_ID_REGISTER, "wrong_syscall_id_register", "calling_convention.syscall_id.register"),
        _expected_value_issue(convention.syscall_id.value_type, _EXPECTED_SYSCALL_ID_TYPE, "wrong_syscall_id_type", "calling_convention.syscall_id.type"),
        _expected_value_issue(convention.payload.register, _EXPECTED_PAYLOAD_REGISTER, "wrong_payload_register", "calling_convention.payload.register"),
        _expected_value_issue(convention.payload.value_type, _EXPECTED_PAYLOAD_TYPE, "wrong_payload_type", "calling_convention.payload.type"),
        _payload_nullability_issue(convention.payload.nullable),
        _expected_value_issue(convention.return_value.register, _EXPECTED_RETURN_REGISTER, "wrong_return_register", "calling_convention.return.register"),
        _expected_value_issue(convention.return_value.value_type, _EXPECTED_RETURN_TYPE, "wrong_return_type", "calling_convention.return.type"),
    )


def _heartbeat_syscall_issue(context: BoundaryContext) -> BoundaryIssue | None:
    heartbeat = context.contract.debug_heartbeat
    return _first_issue(
        _abi_syscall_issue(context, heartbeat.constant, "syscalls.debug_heartbeat.constant"),
        _payload_layout_issue(context),
        _sentinel_issue("request", heartbeat.request, context.manifest.heartbeat.request),
        _sentinel_issue("response", heartbeat.response, context.manifest.heartbeat.response),
    )


def _nop_syscall_issue(context: BoundaryContext) -> BoundaryIssue | None:
    nop = context.contract.nop
    return _first_issue(
        _abi_syscall_issue(context, nop.constant, "syscalls.nop.constant"),
        _nop_payload_argument_issue(nop.payload_argument),
        _status_constant_issue(nop.success_behavior.return_status, context.manifest.constants.status, "syscalls.nop.success_behavior.return_status"),
        _nop_return_status_issue(nop.success_behavior.return_status),
        _nop_mutation_issue(nop.success_behavior.mutates_payload),
    )


def _abi_syscall_issue(
    context: BoundaryContext,
    constant: str,
    contract_field: str,
) -> BoundaryIssue | None:
    if constant in context.manifest.constants.syscalls:
        return None
    return _issue("missing_abi_syscall_constant", contract_field, f"{constant} is not declared in ABI manifest syscalls")


def _nop_payload_argument_issue(payload_argument: str) -> BoundaryIssue | None:
    if payload_argument == "null":
        return None
    return _issue("wrong_nop_payload_argument", "syscalls.nop.payload_argument", f"Expected 'null', got {payload_argument!r}")


def _nop_return_status_issue(return_status: str) -> BoundaryIssue | None:
    if return_status == "K_OK":
        return None
    return _issue("wrong_nop_return_status", "syscalls.nop.success_behavior.return_status", f"Expected K_OK, got {return_status}")


def _nop_mutation_issue(mutates_payload: tuple[str, ...]) -> BoundaryIssue | None:
    if not mutates_payload:
        return None
    return _issue("nop_mutates_payload", "syscalls.nop.success_behavior.mutates_payload", "NOP must not mutate payload fields")


def _payload_layout_issue(context: BoundaryContext) -> BoundaryIssue | None:
    if context.contract.debug_heartbeat.payload_layout == "heartbeat_payload":
        return None
    return _issue("missing_payload_layout", "syscalls.debug_heartbeat.payload_layout", f"{context.contract.debug_heartbeat.payload_layout} is not declared in ABI manifest layouts")


def _sentinel_issue(
    phase: str,
    actual: syscall_boundary_contract.BoundarySentinels,
    expected: abi_manifest.HeartbeatSentinels,
) -> BoundaryIssue | None:
    return _first_issue(
        _expected_value_issue(actual.sequence, expected.sequence, f"{phase}_sentinel_mismatch", f"syscalls.debug_heartbeat.{phase}.sequence"),
        _expected_value_issue(actual.timestamp, expected.timestamp, f"{phase}_sentinel_mismatch", f"syscalls.debug_heartbeat.{phase}.timestamp"),
        _expected_value_issue(actual.status_bits, expected.status_bits, f"{phase}_sentinel_mismatch", f"syscalls.debug_heartbeat.{phase}.status_bits"),
    )


def _invalid_behavior_issue(context: BoundaryContext) -> BoundaryIssue | None:
    invalid_behavior = context.contract.debug_heartbeat.invalid_behavior
    status_constants = context.manifest.constants.status
    return _first_issue(
        _status_constant_issue(invalid_behavior.null_payload, status_constants, "syscalls.debug_heartbeat.invalid_behavior.null_payload"),
        _status_constant_issue(invalid_behavior.bad_sequence, status_constants, "syscalls.debug_heartbeat.invalid_behavior.bad_sequence"),
    )


def _success_behavior_issue(context: BoundaryContext) -> BoundaryIssue | None:
    success_behavior = context.contract.debug_heartbeat.success_behavior
    return _first_issue(
        _status_constant_issue(success_behavior.return_status, context.manifest.constants.status, "syscalls.debug_heartbeat.success_behavior.return_status"),
        _mutable_fields_issue(success_behavior.mutates_payload, _payload_field_names(context.manifest), "syscalls.debug_heartbeat.success_behavior.mutates_payload"),
    )


def _ownership_issue(context: BoundaryContext) -> BoundaryIssue | None:
    ownership = context.contract.ownership
    return _first_issue(
        _expected_value_issue(ownership.payload_owner, _EXPECTED_PAYLOAD_OWNER, "wrong_payload_owner", "ownership.payload_owner"),
        _mutable_fields_issue(ownership.kernel_may_mutate, _payload_field_names(context.manifest), "ownership.kernel_may_mutate"),
        _payload_retention_issue(ownership.kernel_may_retain_payload),
    )


def _proof_ownership_issue(
    contract: syscall_boundary_contract.SyscallBoundaryContract,
) -> BoundaryIssue | None:
    for entry in contract.proof_ownership:
        if entry.validator_name not in CHECKS:
            return _issue("unknown_proof_validator", f"proof_ownership.{entry.validator_name}", f"{entry.validator_name} is not a registered validator")
    return None


def _expected_value_issue(
    actual: object,
    expected: object,
    reason: str,
    contract_field: str,
) -> BoundaryIssue | None:
    if actual == expected:
        return None
    return _issue(reason, contract_field, f"Expected {expected!r}, got {actual!r}")


def _payload_nullability_issue(nullable: bool | None) -> BoundaryIssue | None:
    if nullable is False:
        return None
    return _issue("wrong_payload_nullability", "calling_convention.payload.nullable", f"Expected False, got {nullable!r}")


def _status_constant_issue(
    constant: str,
    status_constants: dict[str, int],
    contract_field: str,
) -> BoundaryIssue | None:
    if constant in status_constants:
        return None
    return _issue("unknown_status_constant", contract_field, f"{constant} is not declared in ABI manifest status constants")


def _mutable_fields_issue(
    actual_fields: tuple[str, ...],
    expected_fields: tuple[str, ...],
    contract_field: str,
) -> BoundaryIssue | None:
    if actual_fields == expected_fields:
        return None
    unknown = tuple(field for field in actual_fields if field not in expected_fields)
    if unknown:
        return _issue("unknown_mutable_field", contract_field, f"{unknown[0]} is not part of the heartbeat payload layout")
    return _issue("mutable_field_set_mismatch", contract_field, f"Expected {expected_fields}, got {actual_fields}")


def _payload_retention_issue(retains_payload: bool) -> BoundaryIssue | None:
    if retains_payload is False:
        return None
    return _issue("payload_retention_forbidden", "ownership.kernel_may_retain_payload", "Kernel may not retain the caller-owned payload pointer")


def _payload_field_names(manifest: abi_manifest.AbiManifest) -> tuple[str, ...]:
    return tuple(field.name for field in manifest.heartbeat_payload.fields)


def _assembly_exports_symbol(source: str, symbol: str) -> bool:
    return re.search(rf"^global\s+{re.escape(symbol)}\s*$", source, re.MULTILINE) is not None


def _assembly_defines_label(source: str, symbol: str) -> bool:
    return re.search(rf"^{re.escape(symbol)}:\s*$", source, re.MULTILINE) is not None


def _first_issue(*issues: BoundaryIssue | None) -> BoundaryIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> BoundaryIssue:
    return BoundaryIssue(reason, contract_field, detail)


def _failure_result(issue: BoundaryIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_BOUNDARY_CONTRACT_INVALID,
        detail=f"Syscall boundary contract invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Keep contracts/syscall_boundary_contract.v0.json aligned with the currently proven heartbeat trap path",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
