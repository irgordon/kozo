from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import FIXED_USER_MAPPING_FOUNDATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.fixed_user_mapping_foundation import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "fixed_user_mapping_foundation.v0.json"
_BOOT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_PAGING_PATH = ROOT / "kernel" / "arch" / "x86_64" / "paging.asm"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"

_MAPPING_MARKERS = (
    "KOZO_USER_MAPPING_INIT_START",
    "KOZO_USER_MAPPING_TABLES_OK",
    "KOZO_USER_MAPPING_PERMISSIONS_OK",
    "KOZO_USER_MAPPING_ACTIVATE_OK",
    "KOZO_USER_MAPPING_SURVIVAL_OK",
)
_TABLE_SYMBOLS = (
    "governed_pml4",
    "governed_kernel_pdpt",
    "governed_kernel_pd",
    "governed_kernel_pt",
    "governed_user_pdpt",
    "governed_user_pd",
    "governed_user_pt",
)
_BACKING_SYMBOLS = (
    "user_probe_code_start",
    "user_probe_code_end",
    "user_probe_data_start",
    "user_probe_data_end",
    "user_probe_stack",
    "user_probe_stack_top",
)
_PROHIBITED_TRANSITIONS = re.compile(
    r"(?im)^\s*(?:iretq|sysretq?|syscall|lgdt|lidt|ltr|wrmsr)\b"
)


@dataclass(frozen=True)
class FixedUserMappingEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class FixedUserMappingEvidenceContext:
    boot: str
    paging: str
    linker: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class FixedUserMappingFoundationEvidenceValidator(BaseValidator):
    name = "fixed_user_mapping_foundation_evidence"
    subsystem = "fixed_user_mapping_foundation_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user mappings align across contract, source, ELF, and QEMU evidence",
        )


def _evidence_issue() -> FixedUserMappingEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    context = _load_context()
    if isinstance(context, FixedUserMappingEvidenceIssue):
        return context
    checks = (
        _boot_sequence_issue,
        _table_construction_issue,
        _permission_construction_issue,
        _activation_issue,
        _walk_issue,
        _survival_issue,
        _ring3_prohibition_issue,
        _linker_geometry_issue,
        _elf_issue,
        _runtime_issue,
    )
    for check in checks:
        issue = check(context)
        if issue is not None:
            return issue
    return None


def _load_context() -> FixedUserMappingEvidenceContext | FixedUserMappingEvidenceIssue:
    sources = {}
    for name, path in (("boot", _BOOT_PATH), ("paging", _PAGING_PATH), ("linker", _LINKER_PATH)):
        if not path.is_file():
            return _issue("missing_source", f"source_files.{name}", f"Missing fixed user-mapping source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, FixedUserMappingEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, FixedUserMappingEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial_log", "QEMU serial log is missing")
    return FixedUserMappingEvidenceContext(
        sources["boot"],
        sources["paging"],
        sources["linker"],
        report,
        metadata,
        _SERIAL_PATH.read_text(errors="replace"),
    )


def _boot_sequence_issue(context: FixedUserMappingEvidenceContext):
    expected = (
        "WRITE_COM1_MARKER simd_probe_ok_marker, simd_probe_ok_marker_end",
        "WRITE_COM1_MARKER user_mapping_init_start_marker, user_mapping_init_start_marker_end",
        "call initialize_fixed_user_mapping_tables",
        "jnz .halt",
        "WRITE_COM1_MARKER user_mapping_tables_ok_marker, user_mapping_tables_ok_marker_end",
        "call validate_fixed_user_mapping_policy",
        "jnz .halt",
        "WRITE_COM1_MARKER user_mapping_permissions_ok_marker, user_mapping_permissions_ok_marker_end",
        "call activate_fixed_user_mapping_root",
        "jnz .halt",
        "WRITE_COM1_MARKER user_mapping_activate_ok_marker, user_mapping_activate_ok_marker_end",
        "call run_fixed_user_mapping_survival_probe",
        "jnz .halt",
        "WRITE_COM1_MARKER user_mapping_survival_ok_marker, user_mapping_survival_ok_marker_end",
        "WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end",
        "call runtime_progression_entry",
    )
    return _ordered_source_issue(
        context.boot,
        expected,
        "mapping_sequence_invalid",
        "success_markers",
    )


def _table_construction_issue(context: FixedUserMappingEvidenceContext):
    required = (
        "clear_fixed_mapping_storage:",
        "lea rdi, [rel governed_page_tables_start]",
        "mov ecx, GOVERNED_TABLE_BYTES / 8",
        "rep stosq",
        "install_fixed_table_hierarchy:",
    )
    issue = _ordered_source_issue(
        context.paging,
        required,
        "page_tables_not_zeroed",
        "page_tables.zero_fill_required",
    )
    if issue is not None:
        return issue
    for symbol in _TABLE_SYMBOLS:
        if f"{symbol}:" not in context.paging:
            return _issue("missing_table_symbol", f"page_tables.{symbol}", f"Missing fixed page-table symbol: {symbol}")
    return None


def _permission_construction_issue(context: FixedUserMappingEvidenceContext):
    upper_entries = (
        "governed_pml4 + USER_PML4_INDEX * 8",
        "governed_user_pdpt + USER_PDPT_INDEX * 8",
        "governed_user_pd + USER_PD_INDEX * 8",
    )
    for entry in upper_entries:
        assignment = re.compile(
            rf"or rax, PTE_PRESENT \| PTE_WRITABLE \| PTE_USER\s+mov \[rel {re.escape(entry)}\], rax",
            re.MULTILINE,
        )
        if assignment.search(context.paging) is None:
            return _issue("missing_upper_level_user", "permission_policy.user_levels", f"U/S is missing from {entry}")
    if "or rax, PTE_PRESENT | PTE_USER" not in context.paging:
        return _issue("code_permission_invalid", "user_regions.user_probe_code", "User code leaf must be user RX")
    if context.paging.count("PTE_PRESENT | PTE_WRITABLE | PTE_USER") < 5:
        return _issue("data_stack_permission_invalid", "user_regions", "User data and stack must be user RW-NX")
    if context.paging.count("mov rdx, PTE_NX") < 4:
        return _issue("nx_policy_missing", "permission_policy", "NX must protect user data, user stack, and writable kernel ranges")
    return None


def _activation_issue(context: FixedUserMappingEvidenceContext):
    expected = (
        "activate_fixed_user_mapping_root:",
        "mov rax, [rel governed_page_table_root_physical]",
        "mov cr3, rax",
        "mov rdx, cr3",
        "mov [rel observed_governed_cr3], rdx",
        "and rax, rcx",
        "and rdx, rcx",
        "cmp rdx, rax",
        "jne .failed",
    )
    return _ordered_source_issue(
        context.paging,
        expected,
        "cr3_readback_missing",
        "activation",
    )


def _walk_issue(context: FixedUserMappingEvidenceContext):
    required = (
        "walk_page_mapping:",
        "test r8, PTE_PRESENT",
        "test r8, PTE_WRITABLE",
        "test r8, PTE_USER",
        "bt r8, 63",
        "fixed_table_virtual_address:",
    )
    return _ordered_source_issue(
        context.paging,
        required,
        "software_walk_invalid",
        "software_walk",
    )


def _survival_issue(context: FixedUserMappingEvidenceContext):
    required = (
        "run_fixed_user_mapping_survival_probe:",
        "cmp qword [rel mapping_kernel_survival_value], rax",
        "push rax",
        "pop rdx",
        "mov rdi, USER_PROBE_DATA_VA",
        "mov [rdi], rax",
        "mov qword [rdi], 0",
        "mov rdi, USER_PROBE_STACK_VA + PAGE_SIZE - 8",
        "mov [rdi], rax",
        "mov qword [rdi], 0",
        "call validate_fixed_user_mapping_policy",
    )
    return _ordered_source_issue(
        context.paging,
        required,
        "survival_probe_invalid",
        "survival_probe",
    )


def _ring3_prohibition_issue(context: FixedUserMappingEvidenceContext):
    combined = f"{context.boot}\n{context.paging}"
    if _PROHIBITED_TRANSITIONS.search(_without_comments(combined)):
        return _issue("privilege_transition_present", "non_goals.Ring 3 execution", "Paging phase must not introduce privilege-transition instructions")
    return None


def _linker_geometry_issue(context: FixedUserMappingEvidenceContext):
    required = (
        ".user_probe_code :",
        ".user_probe_data :",
        ".user_probe_stack :",
        ".paging_tables :",
        "user probe code backing must be one page",
        "user probe data backing must be one page",
        "user probe stack backing must be one page",
        "governed page-table storage must be seven pages",
    )
    for token in required:
        if token not in context.linker:
            return _issue("linker_geometry_invalid", "user_regions", f"Linker mapping geometry is missing: {token}")
    return None


def _elf_issue(context: FixedUserMappingEvidenceContext):
    record = context.report.get("fixed_user_mapping_foundation")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.fixed_user_mapping_foundation", "Kernel ELF report lacks fixed user-mapping evidence")
    symbols = record.get("symbols")
    for symbol in (*_TABLE_SYMBOLS, *_BACKING_SYMBOLS):
        value = symbols.get(symbol) if isinstance(symbols, dict) else None
        if not isinstance(value, dict) or value.get("present") is not True:
            return _issue("missing_elf_symbol", f"kernel_elf_report.fixed_user_mapping_foundation.symbols.{symbol}", f"Kernel ELF lacks {symbol}")
    for field in ("page_table_storage",):
        issue = _range_issue(record.get(field), f"kernel_elf_report.fixed_user_mapping_foundation.{field}", 7 * 4096)
        if issue is not None:
            return issue
    regions = record.get("user_regions")
    for name in ("code", "data", "stack"):
        value = regions.get(name) if isinstance(regions, dict) else None
        issue = _range_issue(value, f"kernel_elf_report.fixed_user_mapping_foundation.user_regions.{name}", 4096)
        if issue is not None:
            return issue
    for field in ("pre_odin_call_order_valid", "cr3_read_present", "cr3_write_present", "software_walk_present"):
        if record.get(field) is not True:
            return _issue("missing_elf_evidence", f"kernel_elf_report.fixed_user_mapping_foundation.{field}", f"Kernel ELF mapping evidence requires {field}")
    if record.get("paging_module_transition_instructions") != []:
        return _issue("privilege_transition_present", "kernel_elf_report.fixed_user_mapping_foundation.paging_module_transition_instructions", "Fixed paging functions must not contain privilege-transition instructions")
    return None


def _runtime_issue(context: FixedUserMappingEvidenceContext):
    expected = list(get_smoke_marker_order())
    observed = context.metadata.get("observed_markers")
    if context.metadata.get("outcome") != "pass" or observed != expected:
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the full governed marker sequence")
    position = -1
    for marker in expected:
        position = context.serial.find(marker, position + 1)
        if position < 0:
            return _issue("runtime_marker_missing", f"qemu_smoke.{marker}", f"QEMU serial log is missing {marker}")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Missing evidence: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence_json", field, f"Invalid evidence JSON: {exc}")
    if not isinstance(value, dict):
        return _issue("invalid_evidence_json", field, "Evidence must be a JSON object")
    return value


def _range_issue(value, field: str, size: int):
    if (
        not isinstance(value, dict)
        or value.get("size_bytes") != size
        or value.get("start_aligned") is not True
    ):
        return _issue("elf_geometry_invalid", field, f"ELF range must be {size} bytes and page-aligned")
    return None


def _ordered_source_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
    lines = tuple(_normalized_lines(source))
    position = -1
    for token in tokens:
        try:
            position = lines.index(token, position + 1)
        except ValueError:
            return _issue(reason, field, f"Missing or misordered source operation: {token}")
    return None


def _normalized_lines(source: str):
    for line in source.splitlines():
        normalized = line.split(";", 1)[0].strip()
        if normalized:
            yield normalized


def _without_comments(source: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines())


def _issue(reason: str, field: str, detail: str) -> FixedUserMappingEvidenceIssue:
    return FixedUserMappingEvidenceIssue(reason, field, detail)


def _failure(issue: FixedUserMappingEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_MAPPING_FOUNDATION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Regenerate fixed user-mapping source, ELF, and QEMU evidence without weakening paging policy",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
