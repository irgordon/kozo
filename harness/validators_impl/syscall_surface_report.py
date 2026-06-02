from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import syscall_surface_report
from harness.abi_manifest import ROOT
from harness.codes import OK, SYSCALL_SURFACE_REPORT_INVALID
from harness.validator import BaseValidator, ValidationResult

_REPORT_PATH = syscall_surface_report.REPORT_PATH
_REPORT_ROOT = ROOT


@dataclass(frozen=True)
class SurfaceReportIssue:
    reason: str
    contract_field: str
    detail: str


class SyscallSurfaceReportValidator(BaseValidator):
    name = "syscall_surface_report"
    subsystem = "syscall_surface_report"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _surface_report_issue(_REPORT_PATH)
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Generated syscall surface report matches the current syscall catalog and contracts",
        )


def _surface_report_issue(report_path: Path) -> SurfaceReportIssue | None:
    if not report_path.is_file():
        return _issue("missing_report_file", "docs/generated/syscall_surface.md", f"Missing report file: {report_path}")
    actual = report_path.read_text()
    expected = syscall_surface_report.expected_report_text(_REPORT_ROOT)
    return _first_issue(
        _source_reference_issue(actual),
        _syscall_issue(actual),
        _syscall_class_issue(actual),
        _manual_edit_issue(actual),
        _stale_report_issue(actual, expected),
    )


def _source_reference_issue(actual: str) -> SurfaceReportIssue | None:
    for reference in syscall_surface_report.SOURCE_REFERENCES:
        if f"`{reference}`" not in actual:
            return _issue("missing_source_reference", "generated_from", f"Missing generated source reference {reference}")
    return None


def _syscall_issue(actual: str) -> SurfaceReportIssue | None:
    for syscall in syscall_surface_report.load_report_inputs(_REPORT_ROOT).catalog.syscalls:
        if f"### {syscall.name}" not in actual:
            return _issue("missing_syscall", f"syscalls.{syscall.name}", f"Missing syscall section {syscall.name}")
    return None


def _syscall_class_issue(actual: str) -> SurfaceReportIssue | None:
    for syscall_class in syscall_surface_report.load_report_inputs(_REPORT_ROOT).classes.classes:
        if f"`{syscall_class.name}`" not in actual:
            return _issue("missing_syscall_class", f"classes.{syscall_class.name}", f"Missing syscall class {syscall_class.name}")
    return None


def _manual_edit_issue(actual: str) -> SurfaceReportIssue | None:
    if "This document is generated. Do not edit manually." in actual:
        return None
    return _issue("manual_edit_detected", "generated_notice", "Generated edit warning is missing or changed")


def _stale_report_issue(actual: str, expected: str) -> SurfaceReportIssue | None:
    if _normalize_newlines(actual) == _normalize_newlines(expected):
        return None
    return _issue("stale_report_content", "docs/generated/syscall_surface.md", "Report content does not match generated output")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n")


def _first_issue(*issues: SurfaceReportIssue | None) -> SurfaceReportIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> SurfaceReportIssue:
    return SurfaceReportIssue(reason, contract_field, detail)


def _failure_result(issue: SurfaceReportIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=SYSCALL_SURFACE_REPORT_INVALID,
        detail=f"Syscall surface report invalid: {issue.reason}: {issue.contract_field}: {issue.detail}",
        action="Regenerate docs/generated/syscall_surface.md from harness.syscall_surface_report",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
