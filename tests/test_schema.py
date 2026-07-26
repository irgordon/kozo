from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from harness.aggregator import run_aggregator
from harness.codes import (
    BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID,
    BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID,
    CODES,
    FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID,
    FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID,
    MEMORY_INITIALIZATION_EVIDENCE_INVALID,
    OK,
    SCHEMA_INVALID,
)
from harness.validator import ValidationResult
from harness.validators_impl.schema import SchemaValidator, validate_named_document

KOZO_NEGATIVE_COVERAGE = {
    "schema": {
        "missing_required_schema_fields": "test_fails_when_required_schema_fields_are_missing",
    }
}


class SchemaValidatorTests(unittest.TestCase):
    def test_fails_when_required_schema_fields_are_missing(self):
        result = SchemaValidator().validate({"todo": {}, "runtime": {}})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SCHEMA_INVALID)

    def test_latest_verify_schema_contains_every_canonical_code(self):
        schema = json.loads(latest_verify_schema_path().read_text())

        for code_enum in verification_code_enums(schema):
            expected_codes = set(CODES)
            if OK not in code_enum:
                expected_codes.remove(OK)
            self.assertTrue(expected_codes.issubset(code_enum))

    def test_memory_evidence_failure_remains_visible_in_aggregate_report(self):
        result = ValidationResult.fail(
            code=MEMORY_INITIALIZATION_EVIDENCE_INVALID,
            detail="Memory evidence failed for regression coverage",
        )
        collected = [("memory_initialization_evidence", "memory_initialization_evidence", result)]

        with patch("harness.aggregator._collect_results", return_value=collected):
            artifact = run_aggregator(
                {},
                changed_files=[],
                evidence_files=[],
                run_id="memory-evidence-schema-regression",
                generated_at="2026-07-24T00:00:00Z",
            )

        validate_named_document("latest_verify", artifact)
        self.assertEqual(artifact["status"], "fail")
        self.assertEqual(artifact["summary_code"], MEMORY_INITIALIZATION_EVIDENCE_INVALID)
        self.assertEqual(artifact["checks"][0]["code"], MEMORY_INITIALIZATION_EVIDENCE_INVALID)
        self.assertEqual(artifact["failed_checks"][0]["code"], MEMORY_INITIALIZATION_EVIDENCE_INVALID)

    def test_privilege_transition_checks_serialize_in_aggregate_report(self):
        collected = [
            (
                "bounded_privilege_transition_probe_contract",
                "bounded_privilege_transition_probe_contract",
                ValidationResult.fail(
                    code=BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID,
                    detail="Contract failure remains visible",
                ),
            ),
            (
                "bounded_privilege_transition_probe_evidence",
                "bounded_privilege_transition_probe_evidence",
                ValidationResult.fail(
                    code=BOUNDED_PRIVILEGE_TRANSITION_PROBE_EVIDENCE_INVALID,
                    detail="Evidence failure remains visible",
                ),
            ),
        ]

        with patch("harness.aggregator._collect_results", return_value=collected):
            artifact = run_aggregator(
                {},
                changed_files=[],
                evidence_files=[],
                run_id="privilege-transition-schema-regression",
                generated_at="2026-07-26T00:00:00Z",
            )

        validate_named_document("latest_verify", artifact)
        self.assertEqual(
            [check["name"] for check in artifact["failed_checks"]],
            [
                "bounded_privilege_transition_probe_contract",
                "bounded_privilege_transition_probe_evidence",
            ],
        )

    def test_fixed_request_checks_serialize_in_aggregate_report(self):
        collected = [
            (
                "fixed_user_request_boundary_contract",
                "fixed_user_request_boundary_contract",
                ValidationResult.fail(
                    code=FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID,
                    detail="Fixed request contract failure remains visible",
                ),
            ),
            (
                "fixed_user_request_boundary_evidence",
                "fixed_user_request_boundary_evidence",
                ValidationResult.fail(
                    code=FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID,
                    detail="Fixed request evidence failure remains visible",
                ),
            ),
        ]
        with patch("harness.aggregator._collect_results", return_value=collected):
            artifact = run_aggregator(
                {},
                changed_files=[],
                evidence_files=[],
                run_id="fixed-user-request-schema-regression",
                generated_at="2026-07-26T00:00:00Z",
            )
        validate_named_document("latest_verify", artifact)
        self.assertEqual(
            [check["code"] for check in artifact["failed_checks"]],
            [
                FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID,
                FIXED_USER_REQUEST_BOUNDARY_EVIDENCE_INVALID,
            ],
        )


def latest_verify_schema_path() -> Path:
    return Path(__file__).resolve().parents[1] / "schemas" / "latest_verify.schema.json"


def verification_code_enums(value) -> list[set[str]]:
    enums: list[set[str]] = []
    if isinstance(value, dict):
        enum = value.get("enum")
        if isinstance(enum, list) and SCHEMA_INVALID in enum:
            enums.append(set(enum))
        for child in value.values():
            enums.extend(verification_code_enums(child))
    elif isinstance(value, list):
        for child in value:
            enums.extend(verification_code_enums(child))
    return enums


if __name__ == "__main__":
    unittest.main()
