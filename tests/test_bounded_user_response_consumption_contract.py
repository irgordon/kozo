from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOUNDED_USER_RESPONSE_CONSUMPTION_CONTRACT_INVALID, OK
from harness.validators_impl import bounded_user_response_consumption_contract as validator_module
from harness.validators_impl.bounded_user_response_consumption_contract import (
    BoundedUserResponseConsumptionContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "bounded_user_response_consumption_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_is_invalid",
        "invalid_execution_point": "test_fails_when_resume_count_changes",
        "invalid_phase_values": "test_fails_when_phase_values_change",
        "invalid_response_consumer": "test_fails_when_resume_rflags_are_unsafe",
        "invalid_response_geometry": "test_fails_when_response_address_changes",
        "invalid_record_geometry": "test_fails_when_record_size_changes",
        "record_overlap": "test_fails_when_record_overlaps_response",
        "invalid_shadow_geometry": "test_fails_when_shadow_size_changes",
        "invalid_shadow_policy": "test_fails_when_shadow_is_user_accessible",
        "missing_ring3_response_check": "test_fails_when_response_check_is_missing",
        "missing_second_frame_validation": "test_fails_when_second_frame_check_is_optional",
        "missing_response_revalidation": "test_fails_when_response_revalidation_is_optional",
        "invalid_record_copy": "test_fails_when_user_pointer_is_allowed",
        "missing_clearing_policy": "test_fails_when_record_clear_size_changes",
        "missing_phase_reset": "test_fails_when_phase_reset_is_optional",
        "invalid_marker_order": "test_fails_when_marker_order_changes",
        "invalid_marker_ownership": "test_fails_when_marker_owner_is_missing",
        "invalid_failure_status": "test_fails_when_failure_status_changes",
        "invalid_halt_behavior": "test_fails_when_terminal_halt_is_not_authoritative",
        "missing_non_goal": "test_fails_when_general_syscall_non_goal_is_missing",
        "claim_boundary_too_broad": "test_fails_when_hostile_code_boundary_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BoundedUserResponseConsumptionContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()
        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove=True)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_contract_file")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(text="{bad")
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_contract_json")

    def test_fails_when_schema_is_invalid(self):
        result = self.validate_fixture(mutate=lambda data: data | {"version": 1})
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "contract_schema_violation")

    def test_fails_when_resume_count_changes(self):
        result = self.validate_fixture(mutate=self.nested("execution_point", "ring3_resume_count", 2))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_execution_point")

    def test_fails_when_phase_values_change(self):
        result = self.validate_fixture(mutate=self.nested("transaction_phases", "response_ready", 2))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_phase_values")

    def test_fails_when_resume_rflags_are_unsafe(self):
        result = self.validate_fixture(mutate=self.nested("response_consumer", "sanitized_rflags", "0x202"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_response_consumer")

    def test_fails_when_response_address_changes(self):
        result = self.validate_fixture(mutate=self.nested("response", "virtual_address", "0x0000400000001090"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_response_geometry")

    def test_fails_when_record_size_changes(self):
        result = self.validate_fixture(mutate=self.nested("consumption_record", "size_bytes", 40))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_record_geometry")

    def test_fails_when_record_overlaps_response(self):
        result = self.validate_fixture(mutate=self.nested("consumption_record", "virtual_address", "0x0000400000001090"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "record_overlap")

    def test_fails_when_shadow_size_changes(self):
        result = self.validate_fixture(mutate=self.nested("kernel_shadow", "size_bytes", 40))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_shadow_geometry")

    def test_fails_when_shadow_is_user_accessible(self):
        result = self.validate_fixture(mutate=self.nested("kernel_shadow", "user_accessible", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_shadow_policy")

    def test_fails_when_response_check_is_missing(self):
        def mutation(data):
            data["ring3_response_checks"].remove("current runtime stage matches")
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_ring3_response_check")

    def test_fails_when_second_frame_check_is_optional(self):
        result = self.validate_fixture(mutate=self.nested("second_frame_validation", "saved_rip_fixed", False))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_second_frame_validation")

    def test_fails_when_response_revalidation_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("response_revalidation", "all_eleven_qwords_match_shadow", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_response_revalidation")

    def test_fails_when_user_pointer_is_allowed(self):
        result = self.validate_fixture(mutate=self.nested("record_copy", "user_supplied_pointer", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_record_copy")

    def test_fails_when_record_clear_size_changes(self):
        result = self.validate_fixture(mutate=self.nested("clearing", "user_record_bytes", 40))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_clearing_policy")

    def test_fails_when_phase_reset_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("phase_reset", "required_before_return_to_odin", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_phase_reset")

    def test_fails_when_marker_order_changes(self):
        mutation = lambda data: data | {"marker_order": list(reversed(data["marker_order"]))}
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_marker_order")

    def test_fails_when_marker_owner_is_missing(self):
        def mutation(data):
            del data["marker_ownership"]["KOZO_FIXED_USER_RESPONSE_OK"]
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_marker_ownership")

    def test_fails_when_failure_status_changes(self):
        result = self.validate_fixture(mutate=self.nested("failure_statuses", "record_invalid", 99))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_failure_status")

    def test_fails_when_terminal_halt_is_not_authoritative(self):
        result = self.validate_fixture(mutate=self.nested("halt_behavior", "terminal_halt_remains_authoritative", False))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_halt_behavior")

    def test_fails_when_general_syscall_non_goal_is_missing(self):
        mutation = lambda data: data | {"non_goals": [value for value in data["non_goals"] if value != "general syscall ABI"]}
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_non_goal")

    def test_fails_when_hostile_code_boundary_is_missing(self):
        def mutation(data):
            data["claim_boundary"]["does_not_prove"].remove("safe execution of arbitrary hostile user code")
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "claim_boundary_too_broad")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate=self.nested("transaction_phases", "consumed", 9))
        self.assertEqual(result.code, BOUNDED_USER_RESPONSE_CONSUMPTION_CONTRACT_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def nested(self, section, field, value):
        def mutation(data):
            data[section][field] = value
            return data
        return mutation

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOUNDED_USER_RESPONSE_CONSUMPTION_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, mutate=None, text=None, remove=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            if not remove:
                source = json.loads(validator_module._CONTRACT_PATH.read_text())
                value = mutate(copy.deepcopy(source)) if mutate else source
                path.write_text(text if text is not None else json.dumps(value))
            original = validator_module._CONTRACT_PATH
            validator_module._CONTRACT_PATH = path
            try:
                return BoundedUserResponseConsumptionContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original


if __name__ == "__main__":
    unittest.main()
