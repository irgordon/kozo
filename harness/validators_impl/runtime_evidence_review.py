from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.codes import OK, RUNTIME_EVIDENCE_REVIEW_INVALID
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_REVIEW_PATH = _ROOT / "docs" / "RUNTIME_EVIDENCE_REVIEW.md"
_RELEASE_EVIDENCE_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"
_RELEASE_CHECKLIST_PATH = _ROOT / "docs" / "RELEASE_CHECKLIST.md"
_REQUIRED_CHECKS_PATH = _ROOT / "docs" / "REQUIRED_CHECKS.md"
_METADATA_PATH = _ROOT / "artifacts" / "runtime" / "runtime_smoke.metadata.json"

_EVIDENCE_TYPE = "runtime-adjacent-object-symbol-smoke"
_LIVE_LOG_PATH = "artifacts/runtime/runtime_smoke.log"
_LIVE_METADATA_PATH = "artifacts/runtime/runtime_smoke.metadata.json"
_RELEASE_LOG_PATH = "artifacts/release/runtime/runtime_smoke.log"
_RELEASE_METADATA_PATH = "artifacts/release/runtime/runtime_smoke.metadata.json"
_SMOKE_VALIDATOR = "runtime_smoke_evidence"
_ACCEPTABLE_CLAIM = "KOZO currently has runtime-adjacent object/symbol smoke evidence for the current kernel build path."
_FORBIDDEN_CLAIMS = (
    "KOZO boots.",
    "KOZO has runtime execution.",
    "KOZO supports userspace.",
    "KOZO supports Linux apps.",
    "KOZO is production ready.",
)
_REVIEW_NON_GOALS = (
    ("missing_qemu_boot_non_goal", "runtime_evidence_review.non_goals.qemu_boot", "This evidence does not prove QEMU boot."),
    (
        "missing_hardware_trap_non_goal",
        "runtime_evidence_review.non_goals.hardware_trap",
        "This evidence does not prove hardware syscall/trap execution.",
    ),
    (
        "missing_linux_non_goal",
        "runtime_evidence_review.non_goals.linux_compatibility",
        "This evidence does not prove Linux compatibility.",
    ),
    (
        "missing_userspace_non_goal",
        "runtime_evidence_review.non_goals.userspace_execution",
        "This evidence does not prove userspace execution.",
    ),
    (
        "missing_process_vfs_scheduler_elf_fd_non_goals",
        "runtime_evidence_review.non_goals.process_model",
        "This evidence does not prove process model behavior.",
    ),
    (
        "missing_process_vfs_scheduler_elf_fd_non_goals",
        "runtime_evidence_review.non_goals.vfs_behavior",
        "This evidence does not prove VFS behavior.",
    ),
    (
        "missing_process_vfs_scheduler_elf_fd_non_goals",
        "runtime_evidence_review.non_goals.scheduler_maturity",
        "This evidence does not prove scheduler maturity.",
    ),
    (
        "missing_process_vfs_scheduler_elf_fd_non_goals",
        "runtime_evidence_review.non_goals.elf_loading",
        "This evidence does not prove ELF loading.",
    ),
    (
        "missing_process_vfs_scheduler_elf_fd_non_goals",
        "runtime_evidence_review.non_goals.file_descriptor_behavior",
        "This evidence does not prove file descriptor behavior.",
    ),
    (
        "missing_production_non_goal",
        "runtime_evidence_review.non_goals.production_readiness",
        "This evidence does not prove production readiness.",
    ),
)
_METADATA_NON_GOALS = (
    "QEMU boot",
    "hardware trap execution",
    "Linux compatibility",
    "userspace execution",
    "process model",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness",
)


@dataclass(frozen=True)
class RequiredReviewText:
    reason: str
    contract_field: str
    text: str


@dataclass(frozen=True)
class RuntimeEvidenceReviewIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeEvidenceReviewValidator(BaseValidator):
    name = "runtime_evidence_review"
    subsystem = "runtime_evidence_review"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_evidence_review_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime evidence review policy names the evidence scope, limits, release gates, and protected metadata",
        )


def _runtime_evidence_review_issue() -> RuntimeEvidenceReviewIssue | None:
    review_issue, review_text = _read_required_text(_REVIEW_PATH, "missing_review_document", "docs.RUNTIME_EVIDENCE_REVIEW")
    if review_issue is not None:
        return review_issue
    release_evidence_issue, release_evidence_text = _read_required_text(
        _RELEASE_EVIDENCE_PATH,
        "missing_release_evidence_link",
        "docs.RELEASE_EVIDENCE",
    )
    if release_evidence_issue is not None:
        return release_evidence_issue
    checklist_issue, checklist_text = _read_required_text(
        _RELEASE_CHECKLIST_PATH,
        "missing_release_checklist_gate",
        "docs.RELEASE_CHECKLIST",
    )
    if checklist_issue is not None:
        return checklist_issue
    checks_issue, checks_text = _read_required_text(_REQUIRED_CHECKS_PATH, "missing_required_checks_reference", "docs.REQUIRED_CHECKS")
    if checks_issue is not None:
        return checks_issue
    metadata_issue, metadata = _load_metadata(_METADATA_PATH)
    if metadata_issue is not None:
        return metadata_issue

    return _first_issue(
        _missing_review_text_issue(review_text),
        _release_evidence_reference_issue(release_evidence_text),
        _release_checklist_gate_issue(checklist_text),
        _required_checks_reference_issue(checks_text),
        _metadata_non_goal_issue(metadata),
    )


def _missing_review_text_issue(review_text: str) -> RuntimeEvidenceReviewIssue | None:
    for required_text in _required_review_texts():
        if required_text.text not in review_text:
            return _issue(
                required_text.reason,
                required_text.contract_field,
                f"Runtime evidence review is missing required text: {required_text.text}",
            )
    return None


def _release_evidence_reference_issue(release_evidence_text: str) -> RuntimeEvidenceReviewIssue | None:
    if "docs/RUNTIME_EVIDENCE_REVIEW.md" in release_evidence_text:
        return None
    return _issue(
        "missing_release_evidence_link",
        "release_evidence.runtime_evidence_review",
        "Release evidence policy must reference docs/RUNTIME_EVIDENCE_REVIEW.md",
    )


def _release_checklist_gate_issue(checklist_text: str) -> RuntimeEvidenceReviewIssue | None:
    required_texts = (
        "Runtime evidence review is complete.",
        "Release is blocked if runtime evidence is overclaimed or missing required non-goals.",
    )
    for text in required_texts:
        if text not in checklist_text:
            return _issue(
                "missing_release_checklist_gate",
                "release_checklist.runtime_evidence_review",
                f"Release checklist must require runtime evidence review text: {text}",
            )
    return None


def _required_checks_reference_issue(checks_text: str) -> RuntimeEvidenceReviewIssue | None:
    required_texts = (
        "Runtime evidence review",
        "runtime_evidence_review",
        "release-only review gate",
    )
    for text in required_texts:
        if text not in checks_text:
            return _issue(
                "missing_required_checks_reference",
                "required_checks.runtime_evidence_review",
                f"Required checks policy must describe runtime evidence review text: {text}",
            )
    return None


def _metadata_non_goal_issue(metadata: dict[str, object]) -> RuntimeEvidenceReviewIssue | None:
    non_goals = metadata.get("does_not_prove")
    if not isinstance(non_goals, list):
        return _issue(
            "metadata_review_non_goal_mismatch",
            "runtime_smoke.metadata.does_not_prove",
            "Runtime smoke metadata does_not_prove must be a list",
        )
    for non_goal in _METADATA_NON_GOALS:
        if non_goal not in non_goals:
            return _issue(
                "metadata_review_non_goal_mismatch",
                f"runtime_smoke.metadata.does_not_prove.{non_goal}",
                f"Runtime smoke metadata is missing review non-goal: {non_goal}",
            )
    return None


def _required_review_texts() -> tuple[RequiredReviewText, ...]:
    return (
        RequiredReviewText("missing_evidence_type", "runtime_evidence_review.evidence_type", f"Evidence type: `{_EVIDENCE_TYPE}`"),
        RequiredReviewText("missing_live_log_path", "runtime_evidence_review.live_log", f"Live evidence log: `{_LIVE_LOG_PATH}`"),
        RequiredReviewText("missing_live_metadata_path", "runtime_evidence_review.live_metadata", f"Live metadata: `{_LIVE_METADATA_PATH}`"),
        RequiredReviewText("missing_release_bundle_path", "runtime_evidence_review.release_log", f"`{_RELEASE_LOG_PATH}`"),
        RequiredReviewText("missing_release_bundle_path", "runtime_evidence_review.release_metadata", f"`{_RELEASE_METADATA_PATH}`"),
        RequiredReviewText("missing_validator_reference", "runtime_evidence_review.validator", f"Validator: `{_SMOKE_VALIDATOR}`"),
        *(RequiredReviewText(reason, contract_field, text) for reason, contract_field, text in _REVIEW_NON_GOALS),
        RequiredReviewText("missing_acceptable_claim", "runtime_evidence_review.acceptable_claim", _ACCEPTABLE_CLAIM),
        *(
            RequiredReviewText("missing_forbidden_claim", f"runtime_evidence_review.forbidden_claims.{claim}", claim)
            for claim in _FORBIDDEN_CLAIMS
        ),
    )


def _read_required_text(path: Path, reason: str, contract_field: str) -> tuple[RuntimeEvidenceReviewIssue | None, str]:
    if not path.is_file():
        return _issue(reason, contract_field, f"Missing required runtime evidence review input: {path}"), ""
    return None, path.read_text()


def _load_metadata(path: Path) -> tuple[RuntimeEvidenceReviewIssue | None, dict[str, object]]:
    if not path.is_file():
        return _issue("metadata_review_non_goal_mismatch", "runtime_smoke.metadata", f"Missing runtime smoke metadata: {path}"), {}
    try:
        metadata = json.loads(path.read_text())
    except json.JSONDecodeError:
        return _issue("metadata_review_non_goal_mismatch", "runtime_smoke.metadata", "Runtime smoke metadata is not valid JSON"), {}
    if not isinstance(metadata, dict):
        return _issue("metadata_review_non_goal_mismatch", "runtime_smoke.metadata", "Runtime smoke metadata must be a JSON object"), {}
    return None, metadata


def _first_issue(*issues: RuntimeEvidenceReviewIssue | None) -> RuntimeEvidenceReviewIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeEvidenceReviewIssue:
    return RuntimeEvidenceReviewIssue(reason, contract_field, detail)


def _failure(issue: RuntimeEvidenceReviewIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_EVIDENCE_REVIEW_INVALID,
        detail=issue.detail,
        action="Keep docs/RUNTIME_EVIDENCE_REVIEW.md, release docs, and runtime metadata aligned with runtime evidence review policy",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
