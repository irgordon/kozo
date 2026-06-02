from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness import abi_manifest, syscall_catalog, syscall_class_contract, syscall_table_contract
from harness.codes import OK, SYSCALL_CATALOG_INVALID
from harness.registry import CHECKS
from harness.validator import BaseValidator, ValidationResult

_CATALOG_PATH = syscall_catalog.CATALOG_PATH
_TABLE_CONTRACT_PATH = syscall_table_contract.CONTRACT_PATH
_CLASS_CONTRACT_PATH = syscall_class_contract.CONTRACT_PATH
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH
_RUST_SERVICE_PATH = abi_manifest.ROOT / "userspace" / "core_service" / "src" / "main.rs"

_NO_PAYLOAD_STATUS_PROOFS = (
    "abi_manifest",
    "protocol_contract_alignment",
    "syscall_table_contract",
    "syscall_class_contract",
    "syscall_table_conformance",
)
_NO_PAYLOAD_RUNTIME_PROOF = "runtime_trap_path"
_PAYLOAD_MUTATING_STATUS_PROOFS = (
    "abi_manifest",
    "protocol_contract_alignment",
    "layout_parity",
    "syscall_boundary_contract",
    "syscall_boundary_conformance",
    "syscall_table_contract",
    "syscall_class_contract",
    "syscall_table_conformance",
    "runtime_trap_path",
    "execution_proof",
    "return_path_proof",
)


@dataclass(frozen=True)
class CatalogIssue:
    reason: str
    catalog_field: str
    detail: str


@dataclass(frozen=True)
class CatalogContext:
    catalog: syscall_catalog.SyscallCatalog
    table_data: dict[str, Any]
    class_contract: syscall_class_contract.SyscallClassContract
    manifest: abi_manifest.AbiManifest
    rust_source: str


class SyscallCatalogValidator(BaseValidator):
    name = "syscall_catalog"
    subsystem = "syscall_catalog"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _catalog_issue(_CATALOG_PATH, _TABLE_CONTRACT_PATH, _CLASS_CONTRACT_PATH, _ABI_MANIFEST_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Syscall catalog v0 summarizes the governed syscall surface without owning canonical ABI values",
        )


def _catalog_issue(
    catalog_path: Path,
    table_path: Path,
    class_path: Path,
    manifest_path: Path,
) -> CatalogIssue | None:
    context = _load_context(catalog_path, table_path, class_path, manifest_path)
    if isinstance(context, CatalogIssue):
        return context
    membership_issue = _catalog_table_membership_issue(context)
    if membership_issue is not None:
        return membership_issue
    return _cataloged_syscall_issue(context)


def _load_context(
    catalog_path: Path,
    table_path: Path,
    class_path: Path,
    manifest_path: Path,
) -> CatalogContext | CatalogIssue:
    catalog = _load_catalog(catalog_path)
    if isinstance(catalog, CatalogIssue):
        return catalog
    table_data = _load_table_data(table_path)
    if isinstance(table_data, CatalogIssue):
        return table_data
    class_contract = _load_class_contract(class_path)
    if isinstance(class_contract, CatalogIssue):
        return class_contract
    manifest = _load_manifest(manifest_path)
    if isinstance(manifest, CatalogIssue):
        return manifest
    rust_source = _load_rust_source()
    if isinstance(rust_source, CatalogIssue):
        return rust_source
    return CatalogContext(catalog, table_data, class_contract, manifest, rust_source)


def _load_catalog(path: Path) -> syscall_catalog.SyscallCatalog | CatalogIssue:
    if not path.is_file():
        return _issue("missing_catalog_file", "catalog", f"Syscall catalog is missing: {path}")
    data = _load_catalog_data(path)
    if isinstance(data, CatalogIssue):
        return data
    return _parse_catalog(data)


def _load_catalog_data(path: Path) -> dict[str, Any] | CatalogIssue:
    try:
        return syscall_catalog.load_catalog_json(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_catalog_json", "catalog", f"Syscall catalog is invalid JSON: {exc}")


def _parse_catalog(data: dict[str, Any]) -> syscall_catalog.SyscallCatalog | CatalogIssue:
    try:
        syscall_catalog.validate_catalog_shape(data)
        return syscall_catalog.parse_syscall_catalog(data)
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("catalog_schema_violation", "catalog", f"Syscall catalog schema violation: {exc}")


def _load_table_data(path: Path) -> dict[str, Any] | CatalogIssue:
    try:
        return syscall_table_contract.load_contract_json(path)
    except (json.JSONDecodeError, OSError) as exc:
        return _issue("table_contract_unavailable", "syscall_table_contract", f"Syscall table contract could not be loaded: {exc}")


def _load_class_contract(path: Path) -> syscall_class_contract.SyscallClassContract | CatalogIssue:
    try:
        return syscall_class_contract.load_syscall_class_contract(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("class_contract_unavailable", "syscall_class_contract", f"Syscall class contract could not be loaded: {exc}")


def _load_manifest(path: Path) -> abi_manifest.AbiManifest | CatalogIssue:
    try:
        return abi_manifest.load_abi_manifest(path)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("abi_manifest_unavailable", "abi_manifest", f"ABI manifest could not be loaded: {exc}")


def _load_rust_source() -> str | CatalogIssue:
    try:
        return _RUST_SERVICE_PATH.read_text()
    except OSError as exc:
        return _issue("rust_source_unavailable", "runtime_probe_present", f"Rust service source could not be read: {exc}")


def _catalog_table_membership_issue(context: CatalogContext) -> CatalogIssue | None:
    table_names = set(_table_syscalls(context.table_data))
    catalog_names = {syscall.name for syscall in context.catalog.syscalls}
    missing = sorted(table_names - catalog_names)
    if missing:
        return _issue("missing_table_entry", f"syscalls.{missing[0]}", f"Table syscall {missing[0]} is missing from the catalog")
    unknown = sorted(catalog_names - table_names)
    if unknown:
        return _issue("unknown_catalog_syscall", f"syscalls.{unknown[0]}", f"Catalog syscall {unknown[0]} is not in the table contract")
    return None


def _cataloged_syscall_issue(context: CatalogContext) -> CatalogIssue | None:
    for syscall in context.catalog.syscalls:
        issue = _single_syscall_issue(context, syscall)
        if issue is not None:
            return issue
    return None


def _single_syscall_issue(
    context: CatalogContext,
    syscall: syscall_catalog.CatalogSyscall,
) -> CatalogIssue | None:
    table_syscall = _table_syscalls(context.table_data)[syscall.name]
    return _first_issue(
        _constant_issue(syscall, table_syscall),
        _numeric_id_issue(context, syscall),
        _kind_issue(syscall, table_syscall),
        _class_issue(syscall, table_syscall),
        _payload_behavior_issue(context, syscall, table_syscall),
        _return_status_issue(syscall, table_syscall),
        _mutation_behavior_issue(syscall, table_syscall),
        _branch_selector_issue(syscall, table_syscall),
        _proof_validator_issue(syscall),
        _runtime_probe_issue(context, syscall),
    )


def _constant_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    if syscall.constant == table_syscall.get("constant"):
        return None
    return _issue("constant_mismatch", f"syscalls.{syscall.name}.constant", f"Expected {table_syscall.get('constant')}, got {syscall.constant}")


def _numeric_id_issue(context: CatalogContext, syscall: syscall_catalog.CatalogSyscall) -> CatalogIssue | None:
    expected = context.manifest.constants.syscalls.get(syscall.constant)
    if syscall.numeric_id == expected:
        return None
    return _issue("numeric_id_mismatch", f"syscalls.{syscall.name}.numeric_id", f"Expected {expected}, got {syscall.numeric_id}")


def _kind_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    if syscall.kind == table_syscall.get("kind"):
        return None
    return _issue("kind_mismatch", f"syscalls.{syscall.name}.kind", f"Expected {table_syscall.get('kind')}, got {syscall.kind}")


def _class_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    if syscall.syscall_class == table_syscall.get("class"):
        return None
    return _issue("class_mismatch", f"syscalls.{syscall.name}.class", f"Expected {table_syscall.get('class')}, got {syscall.syscall_class}")


def _payload_behavior_issue(
    context: CatalogContext,
    syscall: syscall_catalog.CatalogSyscall,
    table_syscall: dict[str, Any],
) -> CatalogIssue | None:
    expected = _expected_payload_behavior(context, table_syscall)
    actual = syscall.payload_behavior
    if (actual.argument, actual.layout, actual.required) == expected:
        return None
    return _issue("payload_behavior_mismatch", f"syscalls.{syscall.name}.payload_behavior", f"Expected {expected}, got {(actual.argument, actual.layout, actual.required)}")


def _return_status_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    if syscall.return_status == table_syscall.get("return_status"):
        return None
    return _issue("return_status_mismatch", f"syscalls.{syscall.name}.return_status", f"Expected {table_syscall.get('return_status')}, got {syscall.return_status}")


def _mutation_behavior_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    expected_fields = tuple(table_syscall.get("mutates_payload", ()))
    expected_mutates = bool(expected_fields)
    actual = syscall.mutation_behavior
    if (actual.mutates_payload, actual.fields) == (expected_mutates, expected_fields):
        return None
    return _issue("mutation_behavior_mismatch", f"syscalls.{syscall.name}.mutation_behavior", f"Expected {(expected_mutates, expected_fields)}, got {(actual.mutates_payload, actual.fields)}")


def _branch_selector_issue(syscall: syscall_catalog.CatalogSyscall, table_syscall: dict[str, Any]) -> CatalogIssue | None:
    if syscall.source_branch_selector == table_syscall.get("branch_selector"):
        return None
    return _issue("branch_selector_mismatch", f"syscalls.{syscall.name}.source_branch_selector", f"Expected {table_syscall.get('branch_selector')}, got {syscall.source_branch_selector}")


def _proof_validator_issue(syscall: syscall_catalog.CatalogSyscall) -> CatalogIssue | None:
    return _first_issue(
        _unknown_proof_validator_issue(syscall),
        _required_proof_validator_issue(syscall),
    )


def _runtime_probe_issue(context: CatalogContext, syscall: syscall_catalog.CatalogSyscall) -> CatalogIssue | None:
    expected = _has_runtime_probe(context.rust_source, syscall.name)
    if syscall.runtime_probe_present == expected:
        return None
    reason = "runtime_probe_false_but_present" if expected else "runtime_probe_true_but_missing"
    return _issue(reason, f"syscalls.{syscall.name}.runtime_probe_present", f"Expected {expected}, got {syscall.runtime_probe_present}")


def _expected_payload_behavior(
    context: CatalogContext,
    table_syscall: dict[str, Any],
) -> tuple[str, str | None, bool]:
    syscall_class = _class_by_name(context.class_contract).get(table_syscall.get("class"))
    if table_syscall.get("kind") == "payload":
        return (
            syscall_class.payload_argument if syscall_class else "pointer",
            table_syscall.get("payload_layout"),
            True,
        )
    return (
        table_syscall.get("payload_argument"),
        None,
        False,
    )


def _unknown_proof_validator_issue(syscall: syscall_catalog.CatalogSyscall) -> CatalogIssue | None:
    for validator in syscall.proof_validators:
        if validator not in CHECKS:
            return _issue("unknown_proof_validator", f"syscalls.{syscall.name}.proof_validators", f"{validator} is not registered")
    return None


def _required_proof_validator_issue(syscall: syscall_catalog.CatalogSyscall) -> CatalogIssue | None:
    required = _required_proofs(syscall)
    for validator in required:
        if validator not in syscall.proof_validators:
            return _issue("missing_required_class_proof", f"syscalls.{syscall.name}.proof_validators", f"{validator} is required for {syscall.syscall_class}")
    return None


def _required_proofs(syscall: syscall_catalog.CatalogSyscall) -> tuple[str, ...]:
    if syscall.syscall_class == "payload_mutating_status":
        return _PAYLOAD_MUTATING_STATUS_PROOFS
    if syscall.runtime_probe_present:
        return (*_NO_PAYLOAD_STATUS_PROOFS, _NO_PAYLOAD_RUNTIME_PROOF)
    return _NO_PAYLOAD_STATUS_PROOFS


def _has_runtime_probe(rust_source: str, syscall_name: str) -> bool:
    function_name = {
        "nop": "nop_request",
        "status": "status_request",
        "debug_heartbeat": "heartbeat_request",
    }.get(syscall_name, "")
    return bool(function_name) and re.search(rf"\bpub\s+fn\s+{re.escape(function_name)}\s*\(", rust_source) is not None


def _table_syscalls(table_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    syscalls = table_data.get("valid_syscalls", {})
    if not isinstance(syscalls, dict):
        return {}
    return {name: syscall for name, syscall in syscalls.items() if isinstance(name, str) and isinstance(syscall, dict)}


def _class_by_name(
    contract: syscall_class_contract.SyscallClassContract,
) -> dict[str, syscall_class_contract.SyscallClass]:
    return {syscall_class.name: syscall_class for syscall_class in contract.classes}


def _first_issue(*issues: CatalogIssue | None) -> CatalogIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, catalog_field: str, detail: str) -> CatalogIssue:
    return CatalogIssue(reason, catalog_field, detail)


def _failure_result(issue: CatalogIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_CATALOG_INVALID,
        detail=f"Syscall catalog invalid: {issue.reason}: {issue.catalog_field}: {issue.detail}",
        action="Keep syscall catalog v0 aligned with ABI manifest, syscall table, syscall class, and live runtime probe contracts",
        meta={"reason": issue.reason, "catalog_field": issue.catalog_field},
    )
