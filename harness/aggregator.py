from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple, Type

from harness.codes import CODES, FAIL, OK, PASS
from harness.registry import (
    ARTIFACT_VERSION,
    CHECKS,
    SUBSYSTEMS,
    SUMMARY_SUBSYSTEM_GENERIC,
)
from harness.validator import BaseValidator, ValidationResult
from harness.validators import VALIDATORS
from harness.validators_impl.schema import validate_named_document

_ALLOWED_STATUS = frozenset({PASS, FAIL})
_ALLOWED_SUBSYSTEMS = frozenset(SUBSYSTEMS.keys())
_EXPECTED_VALIDATOR_ORDER = tuple(CHECKS.keys())
_EXPECTED_SUBSYSTEM_BY_CHECK = dict(CHECKS)


def _validate_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _validate_string_list(values: Sequence[Any], field_name: str) -> List[str]:
    normalized: List[str] = []
    for index, value in enumerate(values):
        normalized.append(_validate_nonempty_string(value, f"{field_name}[{index}]"))
    return normalized


def _validate_validator_coverage_and_order(seen_names: Sequence[str]) -> None:
    if tuple(seen_names) != _EXPECTED_VALIDATOR_ORDER:
        raise ValueError(
            "VALIDATORS must appear in canonical order: "
            f"{list(_EXPECTED_VALIDATOR_ORDER)}"
        )


def _build_validator_map() -> Dict[str, Type[BaseValidator]]:
    validator_map: Dict[str, Type[BaseValidator]] = {}
    for validator_class in VALIDATORS:
        validator_name = _validate_nonempty_string(
            getattr(validator_class, "name", ""),
            f"{validator_class.__name__}.name",
        )
        if validator_name in validator_map:
            raise ValueError(f"Duplicate validator registration for {validator_name!r}")
        validator_map[validator_name] = validator_class

    missing = [name for name in _EXPECTED_VALIDATOR_ORDER if name not in validator_map]
    extra = sorted(set(validator_map) - set(_EXPECTED_VALIDATOR_ORDER))
    if missing:
        raise ValueError(f"VALIDATORS missing canonical checks: {missing}")
    if extra:
        raise ValueError(f"VALIDATORS contains non-canonical checks: {extra}")
    return validator_map


def _normalize_result(name: str, subsystem: str, result: ValidationResult) -> Dict[str, Any]:
    if name not in CHECKS:
        raise ValueError(f"Validator name {name!r} is not canonical")
    if subsystem not in _ALLOWED_SUBSYSTEMS:
        raise ValueError(f"Unknown validator subsystem {subsystem!r} for validator {name!r}")
    if subsystem != _EXPECTED_SUBSYSTEM_BY_CHECK[name]:
        raise ValueError(
            f"Validator {name!r} must use subsystem {_EXPECTED_SUBSYSTEM_BY_CHECK[name]!r}"
        )
    if result.status not in _ALLOWED_STATUS:
        raise ValueError(f"Invalid validator status {result.status!r} for validator {name!r}")
    if result.code not in CODES:
        raise ValueError(f"Unknown validator code {result.code!r} for validator {name!r}")
    if result.status == PASS and result.code != OK:
        raise ValueError(f"Passing validator {name!r} must emit code {OK!r}")
    if result.status == FAIL and result.code == OK:
        raise ValueError(f"Failing validator {name!r} must not emit code {OK!r}")

    check = {
        "name": name,
        "subsystem": subsystem,
        "status": result.status,
        "code": result.code,
        "detail": _validate_nonempty_string(result.detail, f"{name}.detail"),
    }
    sub_results = result.meta.get("sub_results")
    if isinstance(sub_results, list):
        check["sub_results"] = sub_results
    if result.status == PASS:
        return {"check": check, "failed_projection": None}

    failed_projection = {
        "name": name,
        "subsystem": subsystem,
        "code": result.code,
        "detail": check["detail"],
    }
    if result.action:
        failed_projection["action"] = result.action
    action_code = result.meta.get("action_code")
    if isinstance(action_code, str) and action_code:
        failed_projection["action_code"] = action_code
    if "sub_results" in check:
        failed_projection["sub_results"] = check["sub_results"]
    return {"check": check, "failed_projection": failed_projection}


def _build_validation_bundle(
    artifact_bundle: Dict[str, Any],
    changed_files: List[str],
    evidence_files: List[str],
    run_id: str,
    generated_at: str,
) -> Dict[str, Any]:
    bundle = dict(artifact_bundle)
    bundle["changed_files"] = changed_files
    bundle["evidence_files"] = evidence_files
    bundle["run_id"] = run_id
    bundle["generated_at"] = generated_at
    return bundle


def _collect_results(validation_bundle: Dict[str, Any]) -> List[Tuple[str, str, ValidationResult]]:
    validator_map = _build_validator_map()
    seen_names: List[str] = []
    collected: List[Tuple[str, str, ValidationResult]] = []

    for name in _EXPECTED_VALIDATOR_ORDER:
        validator = validator_map[name]()
        validator_name = _validate_nonempty_string(validator.name, "validator.name")
        subsystem = _validate_nonempty_string(validator.subsystem, "validator.subsystem")
        seen_names.append(validator_name)
        collected.append((validator_name, subsystem, validator.validate(validation_bundle)))

    _validate_validator_coverage_and_order(seen_names)
    return collected


def _build_artifact(
    run_id: str,
    checks: List[Dict[str, Any]],
    failed_checks: List[Dict[str, Any]],
    changed_files: List[str],
    evidence_files: List[str],
    generated_at: str,
) -> Dict[str, Any]:
    if failed_checks:
        summary_code = failed_checks[0]["code"]
        summary_subsystem = failed_checks[0]["subsystem"]
        status = FAIL
    else:
        summary_code = OK
        summary_subsystem = SUMMARY_SUBSYSTEM_GENERIC
        status = PASS

    artifact = {
        "artifact_version": ARTIFACT_VERSION,
        "run_id": run_id,
        "status": status,
        "summary_code": summary_code,
        "summary_subsystem": summary_subsystem,
        "summary": {
            "total_checks": len(checks),
            "failed_check_count": len(failed_checks),
        },
        "checks": checks,
        "failed_checks": failed_checks,
        "changed_files": changed_files,
        "evidence_files": evidence_files,
        "generated_at": generated_at,
    }
    validate_named_document("latest_verify", artifact)
    return artifact


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
    validation_bundle = _build_validation_bundle(
        artifact_bundle,
        normalized_changed_files,
        normalized_evidence_files,
        normalized_run_id,
        normalized_generated_at,
    )

    raw_results = _collect_results(validation_bundle)
    normalized = [_normalize_result(name, subsystem, result) for name, subsystem, result in raw_results]
    checks = [entry["check"] for entry in normalized]
    failed_checks = [
        entry["failed_projection"]
        for entry in normalized
        if entry["failed_projection"] is not None
    ]
    return _build_artifact(
        normalized_run_id,
        checks,
        failed_checks,
        normalized_changed_files,
        normalized_evidence_files,
        normalized_generated_at,
    )
