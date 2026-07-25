from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from harness import cpu_extended_state_initialization_contract as contract_module
from harness.abi_manifest import ROOT
from harness.codes import CPU_EXTENDED_STATE_INITIALIZATION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_expected_smoke_marker, get_smoke_marker_order
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_BOOT_SOURCE_PATH = ROOT / "kernel" / "arch" / "x86_64" / "boot.asm"
_ELF_REPORT_PATH = ROOT / "artifacts" / "runtime" / "kernel_elf_report.json"
_METADATA_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.metadata.json"
_SERIAL_LOG_PATH = ROOT / "artifacts" / "runtime" / "qemu_smoke.log"
_TOOLING_BLOCKERS = {"missing_iso_generation_tooling", "missing_qemu_tooling", "missing_boot_image"}


@dataclass(frozen=True)
class CpuExtendedStateEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


@dataclass(frozen=True)
class CpuExtendedStateEvidenceContext:
    contract: contract_module.CpuExtendedStateInitializationContract
    source: str
    lines: tuple[str, ...]


class CpuExtendedStateInitializationEvidenceValidator(BaseValidator):
    name = "cpu_extended_state_initialization_evidence"
    subsystem = "cpu_extended_state_initialization_evidence"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _evidence_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="CPU extended-state initialization is aligned across source, ELF, and runtime evidence",
        )


def _evidence_issue() -> CpuExtendedStateEvidenceIssue | None:
    context = _load_context()
    if isinstance(context, CpuExtendedStateEvidenceIssue):
        return context
    return _first_issue(
        _boot_sequence_issue(context),
        _feature_detection_issue(context),
        _control_state_issue(context),
        _x87_and_sse_issue(context),
        _simd_probe_issue(context),
        _failure_path_issue(context),
        _source_avx_issue(context),
        _elf_evidence_issue(),
        _runtime_evidence_issue(),
    )


def _load_context():
    try:
        contract = contract_module.load_cpu_extended_state_initialization_contract(_CONTRACT_PATH)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"CPU extended-state contract is invalid JSON: {exc}")
    except (OSError, KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"CPU extended-state contract is unavailable or malformed: {exc}")
    if not _BOOT_SOURCE_PATH.is_file():
        return _issue("missing_source", "execution_point.source_file", f"CPU state source is missing: {_BOOT_SOURCE_PATH}")
    source = _BOOT_SOURCE_PATH.read_text()
    return CpuExtendedStateEvidenceContext(contract, source, tuple(_normalized_lines(source)))


def _boot_sequence_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    expected = (
        "WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end",
        "WRITE_COM1_MARKER cpu_ext_state_init_start_marker, cpu_ext_state_init_start_marker_end",
        "call initialize_cpu_extended_state",
        "test eax, eax",
        "jnz .halt",
        "WRITE_COM1_MARKER cpu_ext_state_init_ok_marker, cpu_ext_state_init_ok_marker_end",
        "call run_simd_survival_probe",
        "test eax, eax",
        "jnz .halt",
        "WRITE_COM1_MARKER simd_probe_ok_marker, simd_probe_ok_marker_end",
        "WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end",
        "call runtime_progression_entry",
    )
    return _ordered_issue(context.lines, expected, "initialization_order_invalid", "execution_point")


def _feature_detection_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    expected = (
        "required_cpu_features_available:",
        "xor eax, eax",
        "cpuid",
        "cmp eax, 1",
        "jb .cpuid_unavailable",
        "mov eax, 1",
        "cpuid",
        "and edx, CPU_REQUIRED_FEATURE_MASK",
        "cmp edx, CPU_REQUIRED_FEATURE_MASK",
        "jne .required_feature_missing",
    )
    return _ordered_issue(context.lines, expected, "missing_cpuid_check", "required_cpu_features")


def _control_state_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    configure = (
        "configure_extended_state_controls:",
        "mov rax, cr0",
        "or rax, CR0_REQUIRED_SET_MASK",
        "and rax, ~CR0_REQUIRED_CLEAR_MASK",
        "mov cr0, rax",
        "mov rax, cr4",
        "or rax, CR4_REQUIRED_SET_MASK",
        "and rax, ~CR4_OSXSAVE_MASK",
        "mov cr4, rax",
    )
    verify = (
        "verify_extended_state_controls:",
        "mov rax, cr0",
        "test rdx, CR0_REQUIRED_CLEAR_MASK",
        "mov rax, cr4",
        "test rdx, CR4_OSXSAVE_MASK",
    )
    return _first_issue(
        _ordered_issue(context.lines, configure, "missing_control_configuration", "cr0_policy"),
        _ordered_issue(context.lines, verify, "missing_control_readback", "cr4_policy.readback_required"),
    )


def _x87_and_sse_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    return _first_issue(
        _ordered_issue(
            context.lines,
            (
                "initialize_x87_state:",
                "fninit",
                "fnstcw [rel observed_x87_control_word]",
                "cmp word [rel observed_x87_control_word], 0x037f",
            ),
            "missing_x87_initialization",
            "x87_initialization",
        ),
        _ordered_issue(
            context.lines,
            (
                "initialize_sse_state:",
                "ldmxcsr [rel default_mxcsr]",
                "stmxcsr [rel observed_mxcsr]",
                "cmp dword [rel observed_mxcsr], 0x00001f80",
            ),
            "missing_sse_initialization",
            "sse_initialization",
        ),
    )


def _simd_probe_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    probe = context.contract.simd_probe
    expected = (
        "run_simd_survival_probe:",
        "movdqa xmm0, [rel simd_probe_input]",
        "pxor xmm0, [rel simd_probe_mask]",
        "movdqa [rel simd_probe_result], xmm0",
        f"mov rax, {probe['expected_low']}",
        "cmp qword [rel simd_probe_result], rax",
        f"mov rax, {probe['expected_high']}",
        "cmp qword [rel simd_probe_result + 8], rax",
        "mov qword [rel simd_probe_result], 0",
        "mov qword [rel simd_probe_result + 8], 0",
        "pxor xmm0, xmm0",
    )
    return _ordered_issue(context.lines, expected, "invalid_simd_probe", "simd_probe")


def _failure_path_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    return _first_issue(
        _ordered_issue(
            context.lines,
            (
                "call initialize_cpu_extended_state",
                "test eax, eax",
                "jnz .halt",
                "WRITE_COM1_MARKER cpu_ext_state_init_ok_marker, cpu_ext_state_init_ok_marker_end",
            ),
            "failure_path_reaches_success",
            "runtime_continuation.failure_terminal_behavior",
        ),
        _ordered_issue(
            context.lines,
            (
                "call run_simd_survival_probe",
                "test eax, eax",
                "jnz .halt",
                "WRITE_COM1_MARKER simd_probe_ok_marker, simd_probe_ok_marker_end",
            ),
            "failure_path_reaches_success",
            "simd_probe",
        ),
        _ordered_issue(context.lines, (".halt:", "hlt", "jmp .halt"), "missing_halt_convergence", "runtime_continuation.halt_label"),
    )


def _source_avx_issue(context) -> CpuExtendedStateEvidenceIssue | None:
    source_without_comments = "\n".join(line.split(";", 1)[0] for line in context.source.splitlines())
    patterns = (r"\bxsetbv\b", r"\b(?:ymm|zmm)[0-9]+\b", r"\b(?:vzeroupper|vxorps|vxorpd|vmov[a-z0-9]*)\b")
    if any(re.search(pattern, source_without_comments, re.IGNORECASE) for pattern in patterns):
        return _issue("avx_instruction_present", "avx_prohibition", "Pre-Odin source must not enable or use AVX state")
    return None


def _elf_evidence_issue() -> CpuExtendedStateEvidenceIssue | None:
    report = _load_json(_ELF_REPORT_PATH, "kernel_elf_report")
    if isinstance(report, CpuExtendedStateEvidenceIssue):
        return report
    record = report.get("cpu_extended_state_initialization")
    if not isinstance(record, dict):
        return _issue("missing_elf_evidence", "kernel_elf_report.cpu_extended_state_initialization", "Kernel ELF report must record CPU state evidence")
    return _first_issue(
        _elf_symbol_issue(record),
        _elf_boolean_issue(record, "pre_odin_call_order_valid"),
        _elf_boolean_issue(record, "initialization_call_chain_valid"),
        _elf_instruction_issue(record),
        _elf_probe_geometry_issue(record),
        _elf_avx_issue(record),
    )


def _elf_symbol_issue(record) -> CpuExtendedStateEvidenceIssue | None:
    symbols = record.get("symbols")
    required = ("initialize_cpu_extended_state", "run_simd_survival_probe", "observed_x87_control_word", "observed_mxcsr", "simd_probe_result")
    for symbol in required:
        value = symbols.get(symbol) if isinstance(symbols, dict) else None
        if not isinstance(value, dict) or value.get("present") is not True:
            return _issue("missing_elf_symbol", f"kernel_elf_report.cpu_extended_state_initialization.symbols.{symbol}", f"Kernel ELF is missing CPU state symbol {symbol}")
    return None


def _elf_instruction_issue(record) -> CpuExtendedStateEvidenceIssue | None:
    required = (
        "cpuid_present",
        "fninit_present",
        "fnstcw_present",
        "ldmxcsr_present",
        "stmxcsr_present",
        "simd_probe_instruction_present",
    )
    for field in required:
        issue = _elf_boolean_issue(record, field)
        if issue is not None:
            return issue
    if record.get("cr0_access_count", 0) < 3 or record.get("cr4_access_count", 0) < 3:
        return _issue("missing_control_readback", "kernel_elf_report.cpu_extended_state_initialization", "ELF must retain CR0 and CR4 read-modify-write plus readback")
    if record.get("simd_probe_comparison_count", 0) < 2:
        return _issue("missing_simd_result_validation", "kernel_elf_report.cpu_extended_state_initialization.simd_probe_comparison_count", "ELF must retain both scalar SIMD result comparisons")
    return None


def _elf_boolean_issue(record, field) -> CpuExtendedStateEvidenceIssue | None:
    if record.get(field) is True:
        return None
    return _issue("missing_elf_evidence", f"kernel_elf_report.cpu_extended_state_initialization.{field}", f"Kernel ELF CPU evidence must set {field}")


def _elf_probe_geometry_issue(record) -> CpuExtendedStateEvidenceIssue | None:
    probe = record.get("probe_buffer")
    if not isinstance(probe, dict) or probe.get("size_bytes") != 16 or probe.get("start_aligned") is not True:
        return _issue("invalid_probe_geometry", "kernel_elf_report.cpu_extended_state_initialization.probe_buffer", "SIMD probe buffer must be 16-byte sized and aligned")
    return None


def _elf_avx_issue(record) -> CpuExtendedStateEvidenceIssue | None:
    if record.get("avx_prohibited_instruction_present") is True or record.get("prohibited_instructions"):
        return _issue("avx_instruction_present", "kernel_elf_report.cpu_extended_state_initialization.prohibited_instructions", "Kernel ELF must not contain governed AVX instructions")
    return None


def _runtime_evidence_issue() -> CpuExtendedStateEvidenceIssue | None:
    metadata = _load_json(_METADATA_PATH, "qemu_smoke.metadata")
    if isinstance(metadata, CpuExtendedStateEvidenceIssue):
        return metadata
    if metadata.get("outcome") == "blocked" and metadata.get("blocker_category") in _TOOLING_BLOCKERS:
        return None
    if metadata.get("outcome") != "pass":
        return _issue("runtime_evidence_missing", "qemu_smoke.outcome", "CPU state evidence requires passing QEMU evidence or an allowed local tooling blocker")
    markers = get_smoke_marker_order()
    if metadata.get("expected_marker") != get_expected_smoke_marker() or metadata.get("observed_markers") != list(markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.observed_markers", "QEMU metadata must contain the complete CPU state marker sequence")
    if not _SERIAL_LOG_PATH.is_file() or not _ordered_markers_present(_SERIAL_LOG_PATH.read_text(errors="replace"), markers):
        return _issue("metadata_log_mismatch", "qemu_smoke.serial_log", "QEMU log must contain the ordered CPU state marker sequence")
    return None


def _load_json(path: Path, field: str):
    if not path.is_file():
        return _issue("missing_evidence", field, f"Required CPU state evidence is missing: {path}")
    try:
        value = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return _issue("invalid_evidence", field, f"CPU state evidence is invalid JSON: {exc}")
    return value if isinstance(value, dict) else _issue("invalid_evidence", field, "CPU state evidence must be an object")


def _normalized_lines(source: str) -> list[str]:
    return [
        " ".join(line.split(";", 1)[0].split())
        for line in source.splitlines()
        if line.split(";", 1)[0].strip()
    ]


def _ordered_issue(lines, expected, reason: str, field: str):
    position = -1
    for item in expected:
        position = _line_index(lines, item, position + 1)
        if position is None:
            return _issue(reason, field, f"CPU state path is missing ordered operation: {item}")
    return None


def _line_index(lines, expected: str, start: int = 0):
    return next((index for index in range(start, len(lines)) if lines[index] == expected), None)


def _ordered_markers_present(text: str, markers: tuple[str, ...]) -> bool:
    position = -1
    for marker in markers:
        position = text.find(marker, position + 1)
        if position < 0:
            return False
    return True


def _first_issue(*issues):
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> CpuExtendedStateEvidenceIssue:
    return CpuExtendedStateEvidenceIssue(reason, field, detail)


def _failure(issue: CpuExtendedStateEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=CPU_EXTENDED_STATE_INITIALIZATION_EVIDENCE_INVALID,
        detail=issue.detail,
        action="Keep pre-Odin CPU state source, ELF evidence, QEMU markers, AVX prohibition, and halt convergence aligned",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
