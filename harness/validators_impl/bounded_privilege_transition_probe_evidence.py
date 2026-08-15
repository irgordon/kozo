from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.abi_manifest import ROOT
from harness.codes import BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.runtime_marker_occurrences import marker_occurs_as_governed
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.bounded_privilege_transition_probe_contract import _contract_issue

_CONTRACT_PATH = ROOT / "contracts" / "bounded_privilege_transition_probe_contract.v0.json"
_BOOT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_PRIVILEGE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "privilege_transition.asm"
_LAYOUT_PATH = ROOT / "kernel" / "arch" / "x86_64" / "runtime_layout.inc"
_LINKER_PATH = ROOT / "linker" / "kernel.ld"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"

_MARKERS = (
    "KOZO_PRIVILEGE_TRANSITION_INIT_START",
    "KOZO_PRIVILEGE_TABLES_OK",
    "KOZO_RUNTIME_LOOP_EXIT_OK",
    "KOZO_RING3_ENTER",
    "KOZO_RING3_PROBE_OK",
    "KOZO_RING0_RETURN_OK",
    "KOZO_CAPABILITY_DISPATCH_ENTER",
)
_GEOMETRY = {
    "gdt": (56, 16),
    "tss": (104, 16),
    "idt": (4096, 4096),
    "return_stack": (4096, 4096),
    "double_fault_stack": (4096, 4096),
}
_REQUIRED_SYMBOLS = (
    "initialize_privilege_transition",
    "enter_bounded_ring3_probe",
    "governed_gdt",
    "governed_gdt_end",
    "governed_tss",
    "governed_tss_end",
    "governed_idt",
    "governed_idt_end",
    "privilege_return_stack",
    "privilege_return_stack_top",
    "double_fault_stack",
    "double_fault_stack_top",
    "user_privilege_probe_start",
    "user_privilege_probe_end",
    "privilege_return_handler",
    "privilege_ring0_continuation",
)


@dataclass(frozen=True)
class BoundedPrivilegeTransitionEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class BoundedPrivilegeTransitionEvidenceContext:
    boot: str
    privilege: str
    layout: str
    linker: str
    report: dict[str, object]
    metadata: dict[str, object]
    serial: str


class BoundedPrivilegeTransitionProbeEvidenceValidator(BaseValidator):
    name = "bounded_privilege_transition_probe_evidence"
    subsystem = "bounded_privilege_transition_probe_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="One fixed CPL3 excursion and TSS-backed Ring0 return align across source, ELF, and QEMU evidence",
        )


def _evidence_issue() -> BoundedPrivilegeTransitionEvidenceIssue | None:
    contract_issue = _contract_issue(_CONTRACT_PATH)
    if contract_issue is not None:
        return _issue(contract_issue.reason, contract_issue.contract_field, contract_issue.detail)
    context = _load_context()
    if isinstance(context, BoundedPrivilegeTransitionEvidenceIssue):
        return context
    for check in (
        _boot_sequence_issue,
        _descriptor_issue,
        _entry_issue,
        _user_probe_issue,
        _return_issue,
        _failure_issue,
        _linker_issue,
        _elf_issue,
        _runtime_issue,
    ):
        issue = check(context)
        if issue is not None:
            return issue
    return None


def _load_context():
    sources: dict[str, str] = {}
    source_paths = (
        ("boot", _BOOT_PATH),
        ("privilege", _PRIVILEGE_PATH),
        ("layout", _LAYOUT_PATH),
        ("linker", _LINKER_PATH),
    )
    for name, path in source_paths:
        if not path.is_file():
            return _issue("missing_source", f"source_files.{name}", f"Missing privilege-transition source: {path}")
        sources[name] = path.read_text()
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, BoundedPrivilegeTransitionEvidenceIssue):
        return report
    metadata = _load_json(_METADATA_PATH, "qemu_smoke")
    if isinstance(metadata, BoundedPrivilegeTransitionEvidenceIssue):
        return metadata
    if not _SERIAL_PATH.is_file():
        return _issue("missing_runtime_evidence", "qemu_smoke.serial_log", "QEMU serial log is missing")
    return BoundedPrivilegeTransitionEvidenceContext(
        sources["boot"],
        sources["privilege"],
        sources["layout"],
        sources["linker"],
        report,
        metadata,
        _SERIAL_PATH.read_text(errors="replace"),
    )


def _boot_sequence_issue(context):
    expected = (
        "WRITE_COM1_MARKER user_mapping_survival_ok_marker, user_mapping_survival_ok_marker_end",
        "WRITE_COM1_MARKER privilege_transition_init_start_marker, privilege_transition_init_start_marker_end",
        "call initialize_privilege_transition",
        "jnz .halt",
        "WRITE_COM1_MARKER privilege_tables_ok_marker, privilege_tables_ok_marker_end",
        "WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end",
        "call runtime_progression_entry",
    )
    return _ordered_source_issue(context.boot, expected, "transition_sequence_invalid", "success_markers")


def _descriptor_issue(context):
    required = (
        "call clear_privilege_transition_storage",
        "call initialize_governed_tss",
        "call initialize_governed_gdt",
        "call load_governed_tss",
        "call initialize_governed_idt",
        "call validate_privilege_transition_tables",
        "lgdt [rel governed_gdtr]",
        "retfq",
        "ltr ax",
        "str ax",
        "lidt [rel governed_idtr]",
        "sidt [rel observed_governed_idtr]",
    )
    return _source_tokens_issue(context.privilege, required, "descriptor_setup_invalid", "gdt")


def _entry_issue(context):
    expected = (
        "call validate_user_probe_entry",
        "call runtime_serial_write_ring3_enter_marker",
        "push qword USER_DATA_SELECTOR",
        "push qword USER_RFLAGS",
        "push qword USER_CODE_SELECTOR",
        "push rax",
        "iretq",
        "ud2",
    )
    issue = _ordered_source_issue(context.privilege, expected, "entry_frame_invalid", "entry")
    if issue is not None:
        return issue
    required_layout = (
        "%define USER_PROBE_CODE_VA 0x0000400000000000",
        "%define USER_PROBE_STACK_TOP_VA 0x0000400000003000",
        "%define KOZO_PRIVILEGE_RETURN_VECTOR 0x81",
    )
    return _source_tokens_issue(context.layout, required_layout, "entry_geometry_invalid", "entry")


def _user_probe_issue(context):
    expected = (
        "user_privilege_probe_start:",
        "mov ax, cs",
        "and eax, 3",
        "cmp eax, 3",
        "push rax",
        "pop rcx",
        "mov rdi, FIXED_USER_REQUEST_VA",
        "mov qword [rdi + 24], 0",
        "cmp qword [rdi + 24], 0",
        "popfq",
        "int KOZO_PRIVILEGE_RETURN_VECTOR",
        "ud2",
    )
    issue = _ordered_source_issue(context.privilege, expected, "user_probe_invalid", "probe")
    if issue is not None:
        return issue
    probe_source = _source_range(context.privilege, "user_privilege_probe_start:", "user_privilege_probe_end:")
    if "out " in probe_source or "in " in probe_source:
        return _issue("ring3_serial_io_present", "probe.serial_io_forbidden_in_ring3", "The fixed Ring3 stub must not perform port I/O")
    return None


def _return_issue(context):
    expected = (
        "privilege_return_handler:",
        "mov ss, ax",
        "cmp dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING",
        "je handle_fixed_user_request",
        "cmp dword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_RESPONSE_READY",
        "je handle_fixed_user_response_consumption",
        "handle_fixed_user_request:",
        "call validate_ring3_request_frame",
        "call validate_fixed_user_buffer_ranges",
        "call copy_fixed_user_request_in",
        "call validate_fixed_user_request",
        "call runtime_serial_write_user_runtime_status_service_enter_marker",
        "call build_fixed_user_runtime_status_response",
        "call validate_fixed_user_response",
        "call runtime_serial_write_user_runtime_status_service_ok_marker",
        "call copy_fixed_user_response_out",
        "call validate_fixed_user_response_readback",
        "call prepare_user_response_resume",
        "jmp resume_fixed_user_response_consumer",
        "handle_fixed_user_response_consumption:",
        "call validate_ring3_response_frame",
        "call validate_user_visible_response",
        "call validate_fixed_user_consumption_record",
        "call runtime_serial_write_ring3_probe_marker",
        "mov rsp, [rel saved_odin_return_stack]",
        "jmp privilege_ring0_continuation",
        "privilege_ring0_continuation:",
        "test ax, 3",
        "cmp ax, KERNEL_DATA_SELECTOR",
        "cmp rsp, [rel saved_odin_return_stack]",
        "cmp [rel privilege_probe_state], rax",
        "call fixed_user_buffers_are_zero",
        "call runtime_serial_write_ring0_return_marker",
        "ret",
    )
    return _ordered_source_issue(context.privilege, expected, "return_validation_invalid", "return_boundary")


def _failure_issue(context):
    ranges = (
        ("privilege_fault_sink:", "privilege_double_fault_sink:"),
        ("privilege_double_fault_sink:", None),
    )
    for label, end in ranges:
        source = _source_range(context.privilege, label, end)
        if "jmp boot_terminal_halt" not in source:
            return _issue("fault_halt_missing", "return_boundary.halt_on_fault_required", f"{label} must converge on the terminal halt")
    if "sti" in _without_comments(context.privilege):
        return _issue("interrupts_enabled", "transition.interrupts_enabled", "Privilege transition must keep interrupts disabled")
    return None


def _linker_issue(context):
    required = (
        "governed GDT must contain seven descriptor slots",
        "governed TSS must be exactly 104 bytes",
        "governed IDT must be exactly one page",
        "privilege return stack must be exactly one page",
        "double-fault stack must be exactly one page",
        "user privilege probe must remain inside one code page",
    )
    return _source_tokens_issue(context.linker, required, "linker_geometry_invalid", "source_files.linker")


def _elf_issue(context):
    record = context.report.get("bounded_privilege_transition_probe")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.bounded_privilege_transition_probe", "Kernel ELF report lacks privilege-transition evidence")
    symbols = record.get("symbols")
    for symbol in _REQUIRED_SYMBOLS:
        value = symbols.get(symbol) if isinstance(symbols, dict) else None
        if not isinstance(value, dict) or value.get("present") is not True:
            return _issue("missing_elf_symbol", f"kernel_elf_report.bounded_privilege_transition_probe.symbols.{symbol}", f"Kernel ELF lacks {symbol}")
    for field, (size, alignment) in _GEOMETRY.items():
        issue = _range_issue(record.get(field), f"kernel_elf_report.bounded_privilege_transition_probe.{field}", size, alignment)
        if issue is not None:
            return issue
    required_true = (
        "pre_odin_call_order_valid",
        "lgdt_present",
        "sgdt_present",
        "ltr_present",
        "str_present",
        "lidt_present",
        "sidt_present",
        "iretq_present",
        "int_0x81_present",
        "handler_continuation_jump_present",
        "fault_halt_paths_present",
    )
    for field in required_true:
        if record.get(field) is not True:
            return _issue("missing_elf_evidence", f"kernel_elf_report.bounded_privilege_transition_probe.{field}", f"Kernel ELF privilege evidence requires {field}")
    if record.get("prohibited_instructions") != []:
        return _issue("prohibited_instruction_present", "kernel_elf_report.bounded_privilege_transition_probe.prohibited_instructions", "Privilege path must not use syscall, sysret, swapgs, sti, or wrmsr")
    return None


def _runtime_issue(context):
    expected = list(get_smoke_marker_order())
    if context.metadata.get("outcome") != "pass":
        return _issue("runtime_outcome_invalid", "qemu_smoke.outcome", "QEMU must pass the full governed marker sequence")
    if context.metadata.get("observed_markers") != expected:
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the full governed marker sequence")
    position = -1
    for marker in expected:
        position = context.serial.find(marker, position + 1)
        if position < 0:
            return _issue("runtime_marker_missing", f"qemu_smoke.{marker}", f"QEMU serial log is missing {marker}")
        if marker in _MARKERS and not marker_occurs_as_governed(context.serial, marker, expected):
            return _issue("runtime_marker_duplicate", f"qemu_smoke.{marker}", f"QEMU serial marker count must match the governed occurrence count for {marker}")
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


def _range_issue(value, field: str, size: int, alignment: int):
    if (
        not isinstance(value, dict)
        or value.get("size_bytes") != size
        or value.get("required_alignment_bytes") != alignment
        or value.get("start_aligned") is not True
    ):
        return _issue("elf_geometry_invalid", field, f"ELF range must be {size} bytes and {alignment}-byte aligned")
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


def _source_tokens_issue(source: str, tokens: tuple[str, ...], reason: str, field: str):
    for token in tokens:
        if token not in source:
            return _issue(reason, field, f"Missing source operation: {token}")
    return None


def _source_range(source: str, start: str, end: str | None) -> str:
    start_index = source.find(start)
    if start_index < 0:
        return ""
    end_index = source.find(end, start_index + len(start)) if end is not None else len(source)
    return source[start_index:end_index if end_index >= 0 else len(source)]


def _normalized_lines(source: str):
    for line in source.splitlines():
        normalized = line.split(";", 1)[0].strip()
        if normalized:
            yield normalized


def _without_comments(source: str) -> str:
    return "\n".join(line.split(";", 1)[0] for line in source.splitlines())


def _issue(reason: str, field: str, detail: str) -> BoundedPrivilegeTransitionEvidenceIssue:
    return BoundedPrivilegeTransitionEvidenceIssue(reason, field, detail)


def _failure(issue: BoundedPrivilegeTransitionEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Regenerate bounded privilege-transition source, ELF, and QEMU evidence without broadening the boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
