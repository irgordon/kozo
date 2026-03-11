from __future__ import annotations
from typing import Any, Dict, List, Sequence, Tuple

from harness.registry import ARTIFACT_VERSION, CODES, SUBSYSTEMS, CHECKS
from harness.codes import OK, PASS, FAIL
from harness.validator import ValidationResult
from harness.validators import VALIDATORS

_ALLOWED_STATUS = frozenset({PASS, FAIL})
_ALLOWED_SUBSYSTEMS = frozenset(SUBSYSTEMS.keys())
_EXPECTED_VALIDATOR_ORDER = tuple(CHECKS.keys())
_EXPECTED_SUBSYSTEM_BY_CHECK = dict(CHECKS)

def _validate_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field_name} must be a non-empty string")
    return value

def _validate_string_list(values: Sequence[Any], field_name: str) -> List[str]:
    out: List[str] = []
    for idx, value in enumerate(values):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{field_name}[{idx}] must be a non-empty string")
        out.append(value)
    return out

def _validate_validator_coverage_and_order(seen_names: Sequence[str]) -> None:
    seen_set = frozenset(seen_names)
    expected_set = frozenset(_EXPECTED_VALIDATOR_ORDER)

    missing = sorted(expected_set - seen_set)
    extra = sorted(seen_set - expected_set)

    if missing:
        raise ValueError(f"VALIDATORS missing canonical checks: {missing}")
    if extra:
        raise ValueError(f"VALIDATORS contains non-canonical checks: {extra}")
    if tuple(seen_names) != _EXPECTED_VALIDATOR_ORDER:
        raise ValueError(
            "VALIDATORS must appear in canonical order: "
            f"{list(_EXPECTED_VALIDATOR_ORDER)}"
        )

def _normalize_result(name: str, subsystem: str, result: ValidationResult) -> Dict[str, Any]:
    if name not in CHECKS:
        raise ValueError(f"Validator name {name!r} is not canonical")
    if subsystem not in _ALLOWED_SUBSYSTEMS:
        raise ValueError(f"Unknown validator subsystem {subsystem!r} for validator {name!r}")

    expected_subsystem = _EXPECTED_SUBSYSTEM_BY_CHECK[name]
    if subsystem != expected_subsystem:
        raise ValueError(
            f"Validator {name!r} must use subsystem {expected_subsystem!r}, got {subsystem!r}"
        )

    if result.status not in _ALLOWED_STATUS:
        raise ValueError(f"Invalid validator status {result.status!r} for validator {name!r}")
    if result.code not in CODES:
        raise ValueError(f"Unknown validator code {result.code!r} for validator {name!r}")
    if result.status == PASS and result.code != OK:
        raise ValueError(f"Passing validator {name!r} must emit code {OK!r}, got {result.code!r}")
    if result.status == FAIL and result.code == OK:
        raise ValueError(f"Failing validator {name!r} must not emit code {OK!r}")

    detail = _validate_nonempty_string(result.detail, f"{name}.detail")
    meta = result.meta if isinstance(result.meta, dict) else {}

    check = {
        "name": name,
        "subsystem": subsystem,
        "status": result.status,
        "code": result.code,
        "detail": detail,
    }

    failed_projection = None
    if result.status == FAIL:
        failed_projection = {
            "name": name,
            "subsystem": subsystem,
            "code": result.code,
            "detail": detail,
        }
        action = getattr(result, "action", None)
        if isinstance(action, str) and action:
            failed_projection["action"] = action
        action_code = meta.get("action_code")
        if isinstance(action_code, str) and action_code:
            failed_projection["action_code"] = action_code

    return {"check": check, "failed_projection": failed_projection}

def run_aggregator(
    artifact_bundle: Dict[str, Any],
    changed_files: Sequence[Any],
    evidence_files: Sequence[Any],
    run_id: Any,
    generated_at: Any,
) -> Dict[str, Any]:
    normalized_run_id = _validate_nonempty_string(run_id, "run_id")
    normalized_generated_at = _validate_nonempty_string(generated_at, "generated_at")
    normalized_changed_files = _validate_string_list(changed_files, "changed_files")
    normalized_evidence_files = _validate_string_list(evidence_files, "evidence_files")

    raw_results: List[Tuple[str, str, ValidationResult]] = []
    seen_names: List[str] = []
    seen_name_set = set()

    for validator_class in VALIDATORS:
        validator = validator_class()
        name = _validate_nonempty_string(validator.name, "validator.name")
        subsystem = _validate_nonempty_string(validator.subsystem, "validator.subsystem")

        if name in seen_name_set:
            raise ValueError(f"Duplicate validator name {name!r} in VALIDATORS")
        seen_name_set.add(name)
        seen_names.append(name)

        result = validator.validate(artifact_bundle)
        raw_results.append((name, subsystem, result))

    _validate_validator_coverage_and_order(seen_names)

    normalized = [_normalize_result(name, subsystem, result) for name, subsystem, result in raw_results]

    checks = [entry["check"] for entry in normalized]
    failed_checks = [entry["failed_projection"] for entry in normalized if entry["failed_projection"] is not None]

    if failed_checks:
        status = FAIL
        summary_code = failed_checks[0]["code"]
        summary_subsystem = failed_checks[0]["subsystem"]
    else:
        status = PASS
        summary_code = OK
        summary_subsystem = "generic"

    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": normalized_run_id,
        "status": status,
        "summary_code": summary_code,
        "summary_subsystem": summary_subsystem,
        "summary": {
            "total_checks": len(checks),
            "failed_check_count": len(failed_checks),
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "changed_files": normalized_changed_files,
        "evidence_files": normalized_evidence_files,
        "generated_at": normalized_generated_at,
    }

    if artifact["status"] == PASS:
        if artifact["summary_code"] != OK:
            raise ValueError("Passing artifact must have summary_code='OK'")
        if artifact["summary_subsystem"] != "generic":
            raise ValueError("Passing artifact must have summary_subsystem='generic'")
        if artifact["failed_checks"]:
            raise ValueError("Passing artifact must not contain failed_checks")
        if artifact["summary"]["failed_check_count"] != 0:
            raise ValueError("Passing artifact must have failed_check_count=0")

    if artifact["status"] == FAIL:
        if not artifact["failed_checks"]:
            raise ValueError("Failing artifact must contain at least one failed_check")
        if artifact["summary"]["failed_check_count"] != len(artifact["failed_checks"]):
            raise ValueError("failed_check_count must equal the number of failed_checks")

    if artifact["summary"]["total_checks"] != len(artifact["checks"]):
        raise ValueError("total_checks must equal the number of checks")

    return artifact
