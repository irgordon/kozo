from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIRST_GOVERNED_RUNTIME_CAPABILITY_INVALID, OK
from harness.validators_impl import first_governed_runtime_capability as validator_module
from harness.validators_impl.first_governed_runtime_capability import (
    FirstGovernedRuntimeCapabilityValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "first_governed_runtime_capability": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "invalid_capability_identity": "test_fails_when_capability_identity_is_wrong",
        "invalid_request_geometry": "test_fails_when_request_layout_is_wrong",
        "invalid_response_geometry": "test_fails_when_response_layout_is_wrong",
        "invalid_proven_state": "test_fails_when_response_claims_current_stage",
        "invalid_marker_order": "test_fails_when_marker_order_is_wrong",
        "fallthrough_allowed": "test_fails_when_fallthrough_is_allowed",
        "missing_transition_owner": "test_fails_when_transition_owner_is_missing",
        "invalid_claim_boundary": "test_fails_when_claim_boundary_is_broadened",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FirstGovernedRuntimeCapabilityValidatorTests(unittest.TestCase):
    def test_passes_when_contract_matches_governance(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(contract_text="{not json")

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(lambda value: value | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_capability_identity_is_wrong(self):
        result = self.validate_fixture(
            replace_section("capability", status="planned")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_capability_identity", "capability")

    def test_fails_when_request_layout_is_wrong(self):
        result = self.validate_fixture(replace_field("request", 1, offset_bytes=8))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_request_geometry", "request.fields")

    def test_fails_when_response_layout_is_wrong(self):
        result = self.validate_fixture(replace_field("response", 5, offset_bytes=32))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_response_geometry", "response.fields")

    def test_fails_when_response_claims_current_stage(self):
        result = self.validate_fixture(
            replace_section("response", reported_progression_stage=6, proven_stage_mask=127)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_proven_state", "response.proven_stage_mask")

    def test_fails_when_marker_order_is_wrong(self):
        def mutate(value):
            sequence = list(value["markers"]["ordered_sequence"])
            sequence[1], sequence[2] = sequence[2], sequence[1]
            return value | {"markers": value["markers"] | {"ordered_sequence": sequence}}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_marker_order", "markers.ordered_sequence")

    def test_fails_when_required_marker_is_missing(self):
        result = self.validate_fixture(
            remove_nested_value(
                "markers",
                "ordered_sequence",
                "KOZO_RUNTIME_STATUS_QUERY_OK",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_marker_order", "markers.ordered_sequence")

    def test_fails_when_fallthrough_is_allowed(self):
        result = self.validate_fixture(
            replace_section("terminal_behavior", fallthrough_forbidden=False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "fallthrough_allowed",
            "terminal_behavior.fallthrough_forbidden",
        )

    def test_fails_when_transition_owner_is_missing(self):
        result = self.validate_fixture(
            remove_value(
                "transition_ownership",
                "first_governed_runtime_capability contract owns the CONTROLLED_RUNTIME_LOOP to FIRST_GOVERNED_RUNTIME_CAPABILITY proof boundary",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_transition_owner", "transition_ownership")

    def test_fails_when_claim_boundary_is_broadened(self):
        result = self.validate_fixture(
            remove_nested_value(
                "claim_boundary",
                "does_not_prove",
                "userspace capability access",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_claim_boundary", "claim_boundary.does_not_prove")

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_fixture(remove_value("non_goals", "production readiness"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.production readiness")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(replace_field("request", 1, offset_bytes=8))

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIRST_GOVERNED_RUNTIME_CAPABILITY_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, mutate=None, *, remove_contract=False, contract_text=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            if not remove_contract:
                value = json.loads(validator_module._CONTRACT_PATH.read_text())
                if mutate is not None:
                    value = mutate(value)
                path.write_text(contract_text if contract_text is not None else json.dumps(value))
            original = validator_module._CONTRACT_PATH
            validator_module._CONTRACT_PATH = path
            try:
                return FirstGovernedRuntimeCapabilityValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIRST_GOVERNED_RUNTIME_CAPABILITY_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def replace_section(section, **updates):
    def mutate(value):
        return value | {section: value[section] | updates}

    return mutate


def replace_field(section, index, **updates):
    def mutate(value):
        fields = list(value[section]["fields"])
        fields[index] = fields[index] | updates
        return value | {section: value[section] | {"fields": fields}}

    return mutate


def remove_value(section, target):
    def mutate(value):
        return value | {section: [item for item in value[section] if item != target]}

    return mutate


def remove_nested_value(section, field, target):
    def mutate(value):
        nested = value[section] | {
            field: [item for item in value[section][field] if item != target]
        }
        return value | {section: nested}

    return mutate
