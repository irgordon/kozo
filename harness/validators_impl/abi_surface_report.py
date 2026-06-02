from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import abi_surface_report
from harness.abi_manifest import ROOT
from harness.codes import ABI_SURFACE_REPORT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_REPORT_PATH = abi_surface_report.REPORT_PATH
_REPORT_ROOT = ROOT


@dataclass(frozen=True)
class AbiSurfaceReportIssue:
    reason: str
    contract_field: str
    detail: str


class AbiSurfaceReportValidator(BaseValidator):
    name = "abi_surface_report"
    subsystem = "abi_surface_report"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _abi_surface_report_issue(_REPORT_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Generated ABI surface report matches the current ABI manifest",
        )


def _abi_surface_report_issue(report_path: Path) -> AbiSurfaceReportIssue | None:
    if not report_path.is_file():
        return _issue("missing_report_file", "docs/generated/abi_surface.md", f"Missing report file: {report_path}")
    actual = report_path.read_text()
    expected = abi_surface_report.expected_report_text(_REPORT_ROOT)
    inputs = abi_surface_report.load_report_inputs(_REPORT_ROOT)
    return _first_issue(
        _source_reference_issue(actual, inputs),
        _status_constant_issue(actual, inputs),
        _syscall_constant_issue(actual, inputs),
        _binding_path_issue(actual, inputs),
        _layout_field_issue(actual, inputs),
        _layout_size_alignment_issue(actual, inputs),
        _request_sentinel_issue(actual, inputs),
        _response_sentinel_issue(actual, inputs),
        _manual_edit_issue(actual),
        _stale_report_issue(actual, expected),
    )


def _source_reference_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    manifest = inputs.manifest
    references = (
        abi_surface_report.MANIFEST_REFERENCE,
        manifest.canonical_header,
    )
    for reference in references:
        if f"`{reference}`" not in actual:
            return _issue("missing_source_reference", "source_files", f"Missing source reference {reference}")
    return None


def _status_constant_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    for name, value in _ordered_constants(inputs.manifest.constants.status):
        if _constant_row(name, value) not in actual:
            return _issue("missing_status_constant", f"constants.status.{name}", f"Missing status constant {name}")
    return None


def _syscall_constant_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    for name, value in _ordered_constants(inputs.manifest.constants.syscalls):
        if _constant_row(name, value) not in actual:
            return _issue("missing_syscall_constant", f"constants.syscalls.{name}", f"Missing syscall constant {name}")
    return None


def _binding_path_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    bindings = inputs.manifest.generated_bindings
    expected_paths = (
        ("generated_bindings.rust", bindings.rust),
        ("generated_bindings.odin", bindings.odin),
    )
    for contract_field, path in expected_paths:
        if f"`{path}`" not in actual:
            return _issue("missing_binding_path", contract_field, f"Missing generated binding path {path}")
    return None


def _layout_field_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    for field in inputs.manifest.heartbeat_payload.fields:
        if _layout_field_row(field) not in actual:
            return _issue("missing_layout_field", f"layouts.heartbeat_payload.fields.{field.name}", f"Missing layout field {field.name}")
    return None


def _layout_size_alignment_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    layout = inputs.manifest.heartbeat_payload
    if f"Struct size: {layout.size}" not in actual:
        return _issue("missing_layout_size_alignment", "layouts.heartbeat_payload.size", "Missing heartbeat payload struct size")
    if f"Struct alignment: {layout.alignment}" not in actual:
        return _issue("missing_layout_size_alignment", "layouts.heartbeat_payload.alignment", "Missing heartbeat payload struct alignment")
    return None


def _request_sentinel_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    return _sentinel_issue(actual, "request", inputs.manifest.heartbeat.request)


def _response_sentinel_issue(actual: str, inputs: abi_surface_report.AbiSurfaceInputs) -> AbiSurfaceReportIssue | None:
    return _sentinel_issue(actual, "response", inputs.manifest.heartbeat.response)


def _sentinel_issue(actual: str, label: str, sentinels) -> AbiSurfaceReportIssue | None:
    for field_name in ("sequence", "timestamp", "status_bits"):
        value = getattr(sentinels, field_name)
        if _sentinel_row(field_name, value) not in actual:
            return _issue(f"missing_{label}_sentinel", f"heartbeat.{label}.{field_name}", f"Missing {label} sentinel {field_name}")
    return None


def _manual_edit_issue(actual: str) -> AbiSurfaceReportIssue | None:
    if "This document is generated. Do not edit manually." in actual:
        return None
    return _issue("manual_edit_detected", "generated_notice", "Generated edit warning is missing or changed")


def _stale_report_issue(actual: str, expected: str) -> AbiSurfaceReportIssue | None:
    if _normalize_newlines(actual) == _normalize_newlines(expected):
        return None
    return _issue("stale_report_content", "docs/generated/abi_surface.md", "Report content does not match generated output")


def _constant_row(name: str, value: int) -> str:
    return f"| {name} | {value} |"


def _layout_field_row(field) -> str:
    return f"| {field.name} | {field.width} | {field.offset} |"


def _sentinel_row(field_name: str, value) -> str:
    return f"| {field_name} | `{value}` |"


def _ordered_constants(constants: dict[str, int]) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(constants.items(), key=lambda item: (item[1], item[0])))


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n")


def _first_issue(*issues: AbiSurfaceReportIssue | None) -> AbiSurfaceReportIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> AbiSurfaceReportIssue:
    return AbiSurfaceReportIssue(reason, contract_field, detail)


def _failure_result(issue: AbiSurfaceReportIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=ABI_SURFACE_REPORT_INVALID,
        detail=f"ABI surface report invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Regenerate docs/generated/abi_surface.md from harness.abi_surface_report",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
