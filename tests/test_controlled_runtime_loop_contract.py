from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import CONTROLLED_RUNTIME_LOOP_CONTRACT_INVALID, OK
from harness.validators_impl import controlled_runtime_loop_contract as validator_module
from harness.validators_impl.controlled_runtime_loop_contract import (
    ControlledRuntimeLoopContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "controlled_runtime_loop_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "wrong_stage_status": "test_fails_when_stage_status_is_proven_before_ci",
        "wrong_iteration_limit": "test_fails_when_iteration_limit_is_wrong",
        "missing_backward_edge_requirement": "test_fails_when_backward_edge_is_not_required",
        "invalid_state_definition": "test_fails_when_state_definition_is_wrong",
        "wrong_marker_order": "test_fails_when_marker_order_is_wrong",
        "invalid_status_map": "test_fails_when_status_map_is_wrong",
        "fallthrough_allowed": "test_fails_when_fallthrough_is_allowed",
        "missing_transition_owner": "test_fails_when_transition_owner_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class ControlledRuntimeLoopContractValidatorTests(unittest.TestCase):
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

    def test_fails_when_stage_status_is_proven_before_ci(self):
        result = self.validate_fixture(replace_section("current_state", status="proven"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_stage_status", "current_state.status")

    def test_fails_when_iteration_limit_is_wrong(self):
        result = self.validate_fixture(replace_section("loop", iteration_limit=4))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_iteration_limit", "loop.iteration_limit")

    def test_fails_when_backward_edge_is_not_required(self):
        result = self.validate_fixture(replace_section("loop", backward_edge_required=False))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_backward_edge_requirement", "loop.backward_edge_required")

    def test_fails_when_state_definition_is_wrong(self):
        def mutate(value):
            fields = list(value["state"]["fields"])
            fields[2] = fields[2] | {"final_value": 5}
            return value | {"state": value["state"] | {"fields": fields}}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_state_definition", "state.fields")

    def test_fails_when_marker_order_is_wrong(self):
        def mutate(value):
            markers = list(value["markers"]["ordered_sequence"])
            markers[1], markers[2] = markers[2], markers[1]
            return value | {"markers": value["markers"] | {"ordered_sequence": markers}}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_marker_order", "markers.ordered_sequence")

    def test_fails_when_status_map_is_wrong(self):
        result = self.validate_fixture(replace_section("statuses", accumulator_mismatch=9))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_status_map", "statuses")

    def test_fails_when_fallthrough_is_allowed(self):
        result = self.validate_fixture(replace_section("terminal_behavior", fallthrough_forbidden=False))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "fallthrough_allowed", "terminal_behavior.fallthrough_forbidden")

    def test_fails_when_transition_owner_is_missing(self):
        result = self.validate_fixture(
            remove_value(
                "transition_ownership",
                "controlled_runtime_loop_contract owns the RUNTIME_INITIALIZATION_EVIDENCE to CONTROLLED_RUNTIME_LOOP proof boundary",
            )
        )

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_transition_owner", "transition_ownership")

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_fixture(remove_value("non_goals", "production readiness"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.production readiness")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(lambda value: value | {"architecture": "aarch64"})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CONTROLLED_RUNTIME_LOOP_CONTRACT_INVALID)
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
                return ControlledRuntimeLoopContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CONTROLLED_RUNTIME_LOOP_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def replace_section(section, **updates):
    def mutate(value):
        return value | {section: value[section] | updates}

    return mutate


def remove_value(section, target):
    def mutate(value):
        return value | {section: [item for item in value[section] if item != target]}

    return mutate
