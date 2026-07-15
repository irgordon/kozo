from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import runtime_evidence_taxonomy
from harness.codes import OK, RUNTIME_EVIDENCE_TAXONOMY_INVALID
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = runtime_evidence_taxonomy.CONTRACT_PATH

_REQUIRED_MARKERS = (
    "KOZO_EARLY_0_ENTRY",
    "KOZO_EARLY_1_SERIAL_INIT_START",
    "KOZO_EARLY_2_SERIAL_INIT_OK",
    "KOZO_BOOT_SMOKE_OK",
    "KOZO_STACK_INIT_OK",
    "KOZO_MEMORY_INIT_OK",
    "KOZO_RUNTIME_PROGRESS_ENTRY",
    "KOZO_RUNTIME_INIT_OK",
    "KOZO_RUNTIME_RETURN_OK",
)
_REQUIRED_OUTCOMES = ("pass", "blocked")
_REQUIRED_BLOCKERS = (
    "none",
    "limine_not_reached",
    "kernel_not_loaded",
    "kernel_entry_not_reached",
    "serial_not_initialized",
    "marker_not_emitted",
    "stack_marker_not_emitted",
    "memory_marker_not_emitted",
    "runtime_progression_entry_not_reached",
    "runtime_initialization_not_proven",
    "runtime_return_not_reached",
    "qemu_timeout",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
    "missing_iso_generation_tooling",
    "missing_qemu_serial_evidence",
    "invalid_kernel_elf",
    "missing_load_segments",
    "invalid_kernel_entry",
    "linker_output_invalid",
    "limine_lower_half_phdr",
)
_REQUIRED_NON_GOALS = (
    "hardware trap execution",
    "interrupt handling",
    "complete Odin runtime readiness",
    "dynamic initialization",
    "general stack readiness",
    "general memory management",
    "syscall dispatch",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "scheduler behavior",
    "file descriptor behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class RuntimeEvidenceTaxonomyIssue:
    reason: str
    contract_field: str
    detail: str


class RuntimeEvidenceTaxonomyValidator(BaseValidator):
    name = "runtime_evidence_taxonomy"
    subsystem = "runtime_evidence_taxonomy"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _runtime_evidence_taxonomy_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Runtime evidence taxonomy governs smoke marker and blocker vocabulary",
        )


def _runtime_evidence_taxonomy_issue(contract_path: Path) -> RuntimeEvidenceTaxonomyIssue | None:
    taxonomy = _load_taxonomy(contract_path)
    if isinstance(taxonomy, RuntimeEvidenceTaxonomyIssue):
        return taxonomy
    return _first_issue(
        _required_value_issue(taxonomy.smoke_markers, _REQUIRED_MARKERS, "missing_marker", "smoke_markers"),
        _marker_order_issue(taxonomy),
        _expected_marker_issue(taxonomy),
        _required_value_issue(taxonomy.smoke_outcomes, _REQUIRED_OUTCOMES, "missing_outcome", "smoke_outcomes"),
        _required_value_issue(tuple(taxonomy.blocker_categories.keys()), _REQUIRED_BLOCKERS, "missing_blocker_category", "blocker_categories"),
        _blocker_subset_issue(taxonomy.qemu_smoke_blockers, taxonomy, "qemu_smoke_blockers"),
        _blocker_subset_issue(taxonomy.boot_blocker_categories, taxonomy, "boot_blocker_categories"),
        _blocker_subset_issue(taxonomy.kernel_elf_blockers, taxonomy, "kernel_elf_blockers"),
        _pass_condition_issue(taxonomy),
        _blocked_condition_issue(taxonomy),
        _required_value_issue(taxonomy.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _load_taxonomy(
    path: Path,
) -> runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy | RuntimeEvidenceTaxonomyIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Runtime evidence taxonomy contract is missing: {path}")
    try:
        return runtime_evidence_taxonomy.load_runtime_evidence_taxonomy(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Runtime evidence taxonomy contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Runtime evidence taxonomy contract schema violation: {exc}")


def _marker_order_issue(
    taxonomy: runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy,
) -> RuntimeEvidenceTaxonomyIssue | None:
    if taxonomy.smoke_marker_order == _REQUIRED_MARKERS:
        return None
    return _issue("wrong_marker_order", "smoke_marker_order", "Runtime evidence taxonomy marker order must match the governed smoke sequence")


def _expected_marker_issue(
    taxonomy: runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy,
) -> RuntimeEvidenceTaxonomyIssue | None:
    if taxonomy.expected_smoke_marker != taxonomy.smoke_marker_order[-1]:
        return _issue("expected_marker_not_final", "expected_smoke_marker", "Expected smoke marker must be the final smoke marker")
    if taxonomy.pass_condition.get("expected_marker") != taxonomy.expected_smoke_marker:
        return _issue("expected_marker_not_final", "pass_condition.expected_marker", "Pass condition expected marker must match taxonomy expected marker")
    return None


def _blocker_subset_issue(
    categories: tuple[str, ...],
    taxonomy: runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy,
    field: str,
) -> RuntimeEvidenceTaxonomyIssue | None:
    known = set(taxonomy.blocker_categories)
    for category in categories:
        if category not in known:
            return _issue("missing_blocker_category", f"{field}.{category}", f"{field} contains unknown blocker category {category}")
    return None


def _pass_condition_issue(
    taxonomy: runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy,
) -> RuntimeEvidenceTaxonomyIssue | None:
    if taxonomy.pass_condition.get("outcome") != "pass":
        return _issue("missing_outcome", "pass_condition.outcome", "Pass condition must use pass outcome")
    if taxonomy.pass_condition.get("required_marker_sequence") != "full_ordered_smoke_marker_sequence":
        return _issue("wrong_marker_order", "pass_condition.required_marker_sequence", "Pass condition must require the full ordered marker sequence")
    return None


def _blocked_condition_issue(
    taxonomy: runtime_evidence_taxonomy.RuntimeEvidenceTaxonomy,
) -> RuntimeEvidenceTaxonomyIssue | None:
    if taxonomy.blocked_condition.get("outcome") != "blocked":
        return _issue("missing_outcome", "blocked_condition.outcome", "Blocked condition must use blocked outcome")
    if not taxonomy.blocked_condition.get("required_blocker_category"):
        return _issue("missing_blocker_category", "blocked_condition.required_blocker_category", "Blocked condition must require a blocker category")
    return None


def _required_value_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> RuntimeEvidenceTaxonomyIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            return _issue(reason, f"{field}.{expected}", f"Runtime evidence taxonomy must declare: {expected}")
    return None


def _first_issue(*issues: RuntimeEvidenceTaxonomyIssue | None) -> RuntimeEvidenceTaxonomyIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> RuntimeEvidenceTaxonomyIssue:
    return RuntimeEvidenceTaxonomyIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: RuntimeEvidenceTaxonomyIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_EVIDENCE_TAXONOMY_INVALID,
        detail=issue.detail,
        action="Keep runtime evidence marker and blocker vocabulary aligned with contracts/runtime_evidence_taxonomy.v0.json",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
