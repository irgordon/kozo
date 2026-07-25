from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, RUNTIME_STATE_TRANSITION_CAPABILITY_INVALID
from harness.validators_impl import runtime_state_transition_capability as validator_module
from harness.validators_impl.runtime_state_transition_capability import (
    RuntimeStateTransitionCapabilityValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "runtime_state_transition_capability": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "invalid_capability_identity": "test_fails_when_capability_id_is_wrong",
        "invalid_state_geometry": "test_fails_when_state_geometry_is_wrong",
        "invalid_initial_state": "test_fails_when_initial_state_is_wrong",
        "invalid_request_geometry": "test_fails_when_request_geometry_is_wrong",
        "invalid_response_geometry": "test_fails_when_response_geometry_is_wrong",
        "invalid_transition_policy": "test_fails_when_allowed_transition_is_wrong",
        "missing_volatile_requirement": "test_fails_when_volatile_access_is_not_required",
        "invalid_status_map": "test_fails_when_generation_status_is_renumbered",
        "invalid_marker_order": "test_fails_when_marker_order_is_wrong",
        "invalid_failure_behavior": "test_fails_when_rollback_is_not_required",
        "invalid_claim_boundary": "test_fails_when_userspace_boundary_is_removed",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class RuntimeStateTransitionCapabilityValidatorTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(contract_text="{bad json")

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(lambda value: value | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_capability_id_is_wrong(self):
        result = self.validate_fixture(replace_section("capability", numeric_identifier=3))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_capability_identity", "capability")

    def test_fails_when_state_geometry_is_wrong(self):
        result = self.validate_fixture(replace_section("state", size_bytes=24))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_state_geometry", "state")

    def test_fails_when_initial_state_is_wrong(self):
        result = self.validate_fixture(
            replace_nested("state", "initial_values", state=0)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_initial_state", "state.initial_values")

    def test_fails_when_request_geometry_is_wrong(self):
        result = self.validate_fixture(replace_section("request", size_bytes=40))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_request_geometry", "request")

    def test_fails_when_response_geometry_is_wrong(self):
        result = self.validate_fixture(replace_section("response", alignment_bytes=4))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_response_geometry", "response")

    def test_fails_when_allowed_transition_is_wrong(self):
        result = self.validate_fixture(replace_section("transition", allowed_to_state=1))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_transition_policy", "transition")

    def test_fails_when_generation_change_is_wrong(self):
        result = self.validate_fixture(replace_section("transition", generation_increment=2))

        self.assert_failure(result, "invalid_transition_policy", "transition")

    def test_fails_when_volatile_access_is_not_required(self):
        result = self.validate_fixture(
            replace_section("state", volatile_access_required=False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(
            result,
            "invalid_state_policy",
            "state.volatile_access_required",
        )

    def test_fails_when_generation_status_is_renumbered(self):
        result = self.validate_fixture(replace_section("statuses", stale_generation=20))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_status_map", "statuses")

    def test_fails_when_marker_order_is_wrong(self):
        def mutate(value):
            sequence = list(value["markers"]["ordered_sequence"])
            sequence[0], sequence[1] = sequence[1], sequence[0]
            return value | {"markers": value["markers"] | {"ordered_sequence": sequence}}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_marker_order", "markers.ordered_sequence")

    def test_fails_when_rollback_is_not_required(self):
        result = self.validate_fixture(
            replace_section("failure_behavior", readback_failure_restores_previous_state=False)
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_failure_behavior", "failure_behavior")

    def test_fails_when_userspace_boundary_is_removed(self):
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
        result = self.validate_fixture(
            remove_value("non_goals", "production readiness")
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.production readiness")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(replace_section("state", size_bytes=24))

        self.assertEqual(result.code, RUNTIME_STATE_TRANSITION_CAPABILITY_INVALID)
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
                return RuntimeStateTransitionCapabilityValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, RUNTIME_STATE_TRANSITION_CAPABILITY_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def replace_section(section, **updates):
    return lambda value: value | {section: value[section] | updates}


def replace_nested(section, field, **updates):
    def mutate(value):
        nested = value[section] | {field: value[section][field] | updates}
        return value | {section: nested}

    return mutate


def remove_value(section, target):
    return lambda value: value | {
        section: [item for item in value[section] if item != target]
    }


def remove_nested_value(section, field, target):
    def mutate(value):
        nested = value[section] | {
            field: [item for item in value[section][field] if item != target]
        }
        return value | {section: nested}

    return mutate


if __name__ == "__main__":
    unittest.main()
