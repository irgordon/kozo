from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness import abi_manifest, syscall_class_contract, syscall_table_contract
from harness.codes import OK, SYSCALL_CLASS_CONTRACT_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = syscall_class_contract.CONTRACT_PATH
_TABLE_CONTRACT_PATH = syscall_table_contract.CONTRACT_PATH
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH

_NO_PAYLOAD_CLASS = "no_payload_status"
_PAYLOAD_MUTATING_CLASS = "payload_mutating_status"
_EXPECTED_CLASS_BY_KIND = {
    "no_payload": _NO_PAYLOAD_CLASS,
    "payload": _PAYLOAD_MUTATING_CLASS,
}


@dataclass(frozen=True)
class ClassIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class ClassContext:
    contract: syscall_class_contract.SyscallClassContract
    table_data: dict[str, Any]
    manifest: abi_manifest.AbiManifest


class SyscallClassContractValidator(BaseValidator):
    name = "syscall_class_contract"
    subsystem = "syscall_class_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _class_contract_issue(_CONTRACT_PATH, _TABLE_CONTRACT_PATH, _ABI_MANIFEST_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Syscall class contract v0 matches the currently proven syscall table classes",
        )


def _class_contract_issue(
    contract_path: Path,
    table_path: Path,
    manifest_path: Path,
) -> ClassIssue | None:
    context = _load_context(contract_path, table_path, manifest_path)
    if isinstance(context, ClassIssue):
        return context
    classes = _classes_by_name(context.contract)
    syscalls = _table_syscalls(context.table_data)
    return _first_issue(
        _required_class_issue(classes, _NO_PAYLOAD_CLASS, "missing_no_payload_status_class"),
        _required_class_issue(classes, _PAYLOAD_MUTATING_CLASS, "missing_payload_mutating_status_class"),
        _class_semantics_issue(classes),
        _example_issue(classes, syscalls),
        _syscall_class_issue(context, classes, syscalls),
    )


def _load_context(
    contract_path: Path,
    table_path: Path,
    manifest_path: Path,
) -> ClassContext | ClassIssue:
    contract = _load_contract(contract_path)
    if isinstance(contract, ClassIssue):
        return contract
    table_data = _load_table_data(table_path)
    if isinstance(table_data, ClassIssue):
        return table_data
    manifest = _load_manifest(manifest_path)
    if isinstance(manifest, ClassIssue):
        return manifest
    return ClassContext(contract, table_data, manifest)


def _load_contract(path: Path) -> syscall_class_contract.SyscallClassContract | ClassIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Syscall class contract is missing: {path}")
    data = _load_class_data(path)
    if isinstance(data, ClassIssue):
        return data
    return _parse_contract(data)


def _load_class_data(path: Path) -> dict[str, Any] | ClassIssue:
    try:
        return syscall_class_contract.load_contract_json(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Syscall class contract is invalid JSON: {exc}")


def _parse_contract(data: dict[str, Any]) -> syscall_class_contract.SyscallClassContract | ClassIssue:
    try:
        syscall_class_contract.validate_contract_shape(data)
        return syscall_class_contract.parse_syscall_class_contract(data)
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Syscall class contract schema violation: {exc}")


def _load_table_data(path: Path) -> dict[str, Any] | ClassIssue:
    try:
        return syscall_table_contract.load_contract_json(path)
    except (json.JSONDecodeError, OSError) as exc:
        return _issue("table_contract_unavailable", "syscall_table_contract", f"Syscall table contract could not be loaded: {exc}")


def _load_manifest(path: Path) -> abi_manifest.AbiManifest | ClassIssue:
    try:
        return abi_manifest.load_abi_manifest(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("abi_manifest_unavailable", "abi_manifest", f"ABI manifest could not be loaded: {exc}")


def _classes_by_name(
    contract: syscall_class_contract.SyscallClassContract,
) -> dict[str, syscall_class_contract.SyscallClass]:
    return {syscall_class.name: syscall_class for syscall_class in contract.classes}


def _table_syscalls(table_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    syscalls = table_data.get("valid_syscalls", {})
    if isinstance(syscalls, dict):
        return {name: data for name, data in syscalls.items() if isinstance(name, str) and isinstance(data, dict)}
    return {}


def _required_class_issue(
    classes: dict[str, syscall_class_contract.SyscallClass],
    class_name: str,
    reason: str,
) -> ClassIssue | None:
    if class_name in classes:
        return None
    return _issue(reason, f"classes.{class_name}", f"Required syscall class {class_name} is missing")


def _class_semantics_issue(classes: dict[str, syscall_class_contract.SyscallClass]) -> ClassIssue | None:
    return _first_issue(
        _no_payload_class_issue(classes.get(_NO_PAYLOAD_CLASS)),
        _payload_mutating_class_issue(classes.get(_PAYLOAD_MUTATING_CLASS)),
    )


def _no_payload_class_issue(syscall_class: syscall_class_contract.SyscallClass | None) -> ClassIssue | None:
    if syscall_class is None:
        return None
    expected = {
        "payload_argument": "null",
        "payload_layout_required": False,
        "request_required": False,
        "response_required": False,
        "mutates_payload": "forbidden",
        "return_status_required": True,
    }
    return _expected_class_values_issue(syscall_class, expected, "malformed_no_payload_status")


def _payload_mutating_class_issue(syscall_class: syscall_class_contract.SyscallClass | None) -> ClassIssue | None:
    if syscall_class is None:
        return None
    expected = {
        "payload_argument": "pointer",
        "payload_layout_required": True,
        "request_required": True,
        "response_required": True,
        "mutates_payload": "required",
        "return_status_required": True,
        "invalid_behavior_required": ("null_payload", "bad_sequence"),
    }
    return _expected_class_values_issue(syscall_class, expected, "malformed_payload_mutating_status")


def _expected_class_values_issue(
    syscall_class: syscall_class_contract.SyscallClass,
    expected: dict[str, object],
    reason: str,
) -> ClassIssue | None:
    for field, value in expected.items():
        if getattr(syscall_class, field) != value:
            return _issue(reason, f"classes.{syscall_class.name}.{field}", f"Expected {value!r}")
    return None


def _example_issue(
    classes: dict[str, syscall_class_contract.SyscallClass],
    syscalls: dict[str, dict[str, Any]],
) -> ClassIssue | None:
    for syscall_class in classes.values():
        for example in syscall_class.valid_examples:
            if example not in syscalls:
                return _issue("unknown_example_syscall", f"classes.{syscall_class.name}.valid_examples", f"{example} is not in syscall table contract")
    return None


def _syscall_class_issue(
    context: ClassContext,
    classes: dict[str, syscall_class_contract.SyscallClass],
    syscalls: dict[str, dict[str, Any]],
) -> ClassIssue | None:
    for name, syscall in syscalls.items():
        issue = _single_syscall_issue(context, classes, name, syscall)
        if issue is not None:
            return issue
    return None


def _single_syscall_issue(
    context: ClassContext,
    classes: dict[str, syscall_class_contract.SyscallClass],
    name: str,
    syscall: dict[str, Any],
) -> ClassIssue | None:
    syscall_class = syscall.get("class")
    if not isinstance(syscall_class, str) or not syscall_class.strip():
        return _issue("missing_syscall_class", f"valid_syscalls.{name}.class", f"{name} must declare a syscall class")
    return _first_issue(
        _unknown_class_issue(classes, name, syscall_class),
        _expected_named_class_issue(name, syscall_class),
        _kind_class_issue(name, syscall),
        _class_shape_issue(context, name, syscall),
    )


def _unknown_class_issue(
    classes: dict[str, syscall_class_contract.SyscallClass],
    syscall_name: str,
    class_name: str,
) -> ClassIssue | None:
    if class_name in classes:
        return None
    return _issue("unknown_syscall_class", f"valid_syscalls.{syscall_name}.class", f"{class_name} is not declared in syscall class contract")


def _expected_named_class_issue(syscall_name: str, class_name: str) -> ClassIssue | None:
    expected = {"nop": _NO_PAYLOAD_CLASS, "status": _NO_PAYLOAD_CLASS, "debug_heartbeat": _PAYLOAD_MUTATING_CLASS}.get(syscall_name)
    if expected is None or class_name == expected:
        return None
    reason = _wrong_class_reason(syscall_name)
    return _issue(reason, f"valid_syscalls.{syscall_name}.class", f"Expected {expected}, got {class_name}")


def _wrong_class_reason(syscall_name: str) -> str:
    if syscall_name == "nop":
        return "nop_wrong_class"
    if syscall_name == "status":
        return "status_wrong_class"
    return "heartbeat_wrong_class"


def _kind_class_issue(syscall_name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    expected = _EXPECTED_CLASS_BY_KIND.get(syscall.get("kind"))
    if expected is None or syscall.get("class") == expected:
        return None
    return _issue("kind_class_mismatch", f"valid_syscalls.{syscall_name}.class", f"{syscall.get('kind')} must use {expected}")


def _class_shape_issue(context: ClassContext, name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    if syscall.get("class") == _NO_PAYLOAD_CLASS:
        return _no_payload_syscall_issue(name, syscall, context.manifest)
    if syscall.get("class") == _PAYLOAD_MUTATING_CLASS:
        return _payload_mutating_syscall_issue(name, syscall, context.manifest)
    return None


def _no_payload_syscall_issue(
    name: str,
    syscall: dict[str, Any],
    manifest: abi_manifest.AbiManifest,
) -> ClassIssue | None:
    return _first_issue(
        _status_issue(name, syscall.get("return_status"), manifest),
        _payload_argument_issue(name, syscall),
        _empty_mutates_payload_issue(name, syscall),
        _forbidden_field_issue(name, syscall, "payload_layout", "no_payload_has_layout"),
        _forbidden_field_issue(name, syscall, "request", "no_payload_has_request"),
        _forbidden_field_issue(name, syscall, "response", "no_payload_has_response"),
        _no_payload_mutation_issue(name, syscall),
    )


def _payload_mutating_syscall_issue(
    name: str,
    syscall: dict[str, Any],
    manifest: abi_manifest.AbiManifest,
) -> ClassIssue | None:
    return _first_issue(
        _status_issue(name, syscall.get("return_status"), manifest),
        _required_field_issue(name, syscall, "payload_layout", "payload_missing_layout"),
        _required_field_issue(name, syscall, "request", "payload_missing_request"),
        _required_field_issue(name, syscall, "response", "payload_missing_response"),
        _invalid_behavior_issue(name, syscall),
        _payload_layout_issue(name, syscall, manifest),
        _payload_mutation_issue(name, syscall, manifest),
    )


def _status_issue(
    syscall_name: str,
    status: object,
    manifest: abi_manifest.AbiManifest,
) -> ClassIssue | None:
    if isinstance(status, str) and status in manifest.constants.status:
        return None
    return _issue("unknown_status_constant", f"valid_syscalls.{syscall_name}.return_status", f"{status!r} is not a known status constant")


def _payload_argument_issue(syscall_name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    if syscall.get("payload_argument") == "null":
        return None
    return _issue("wrong_no_payload_argument", f"valid_syscalls.{syscall_name}.payload_argument", "No-payload status syscalls must use a null payload argument")


def _empty_mutates_payload_issue(syscall_name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    mutations = syscall.get("mutates_payload")
    if isinstance(mutations, list) and not mutations:
        return None
    return _issue("no_payload_mutates_payload", f"valid_syscalls.{syscall_name}.mutates_payload", "No-payload status syscalls must declare no payload mutations")


def _forbidden_field_issue(
    syscall_name: str,
    syscall: dict[str, Any],
    field: str,
    reason: str,
) -> ClassIssue | None:
    if field not in syscall:
        return None
    return _issue(reason, f"valid_syscalls.{syscall_name}.{field}", f"{field} is forbidden for this syscall class")


def _no_payload_mutation_issue(syscall_name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    if syscall.get("must_not_mutate_payload") is True:
        return None
    return _issue("no_payload_mutates_payload", f"valid_syscalls.{syscall_name}.must_not_mutate_payload", "No-payload status syscalls must forbid payload mutation")


def _required_field_issue(
    syscall_name: str,
    syscall: dict[str, Any],
    field: str,
    reason: str,
) -> ClassIssue | None:
    if field in syscall:
        return None
    return _issue(reason, f"valid_syscalls.{syscall_name}.{field}", f"{field} is required for this syscall class")


def _payload_layout_issue(
    syscall_name: str,
    syscall: dict[str, Any],
    manifest: abi_manifest.AbiManifest,
) -> ClassIssue | None:
    layout = syscall.get("payload_layout")
    if layout == "heartbeat_payload":
        return None
    return _issue("payload_missing_layout", f"valid_syscalls.{syscall_name}.payload_layout", f"{layout!r} is not a known payload layout")


def _invalid_behavior_issue(syscall_name: str, syscall: dict[str, Any]) -> ClassIssue | None:
    behavior = syscall.get("invalid_behavior")
    if not isinstance(behavior, dict):
        return _issue("malformed_payload_mutating_status", f"valid_syscalls.{syscall_name}.invalid_behavior", "Payload-mutating syscalls must declare invalid behavior")
    for field in ("null_payload", "bad_sequence"):
        if field not in behavior:
            return _issue("malformed_payload_mutating_status", f"valid_syscalls.{syscall_name}.invalid_behavior.{field}", f"{field} is required")
    return None


def _payload_mutation_issue(
    syscall_name: str,
    syscall: dict[str, Any],
    manifest: abi_manifest.AbiManifest,
) -> ClassIssue | None:
    fields = tuple(syscall.get("mutates_payload", ()))
    if not fields:
        return _issue("payload_unknown_mutation_field", f"valid_syscalls.{syscall_name}.mutates_payload", "Payload-mutating status syscalls must declare mutated fields")
    if syscall.get("payload_layout") != "heartbeat_payload":
        return None
    layout_fields = {field.name for field in manifest.heartbeat_payload.fields}
    unknown = tuple(field for field in fields if field not in layout_fields)
    if not unknown:
        return None
    return _issue("payload_unknown_mutation_field", f"valid_syscalls.{syscall_name}.mutates_payload", f"{unknown[0]} is not in the payload layout")


def _first_issue(*issues: ClassIssue | None) -> ClassIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> ClassIssue:
    return ClassIssue(reason, contract_field, detail)


def _failure_result(issue: ClassIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_CLASS_CONTRACT_INVALID,
        detail=f"Syscall class contract invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Keep syscall class contract v0 aligned with the currently proven syscall table shapes",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
