from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID, OK
from harness.validators_impl import fixed_user_request_boundary_contract as validator_module
from harness.validators_impl.fixed_user_request_boundary_contract import (
    FixedUserRequestBoundaryContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_request_boundary_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_is_invalid",
        "invalid_execution_point": "test_fails_when_boundary_returns_to_ring3",
        "invalid_request_geometry": "test_fails_when_request_payload_changes",
        "invalid_response_geometry": "test_fails_when_response_layout_changes",
        "invalid_user_span": "test_fails_when_response_exceeds_page",
        "invalid_shadow_geometry": "test_fails_when_shadow_size_changes",
        "invalid_shadow_policy": "test_fails_when_shadow_is_user_accessible",
        "invalid_service_identity": "test_fails_when_service_identifier_changes",
        "invalid_response_token_rule": "test_fails_when_response_mask_changes",
        "service_crosses_copy_boundary": "test_fails_when_service_reads_user_memory",
        "missing_copy_requirement": "test_fails_when_frame_validation_is_optional",
        "caller_controlled_copy": "test_fails_when_user_pointer_is_allowed",
        "invalid_copy_size": "test_fails_when_copy_size_changes",
        "invalid_page_policy": "test_fails_when_page_becomes_executable",
        "missing_buffer_clear": "test_fails_when_post_copy_clear_is_optional",
        "missing_buffer_clear_readback": "test_fails_when_zero_readback_is_optional",
        "invalid_clear_size": "test_fails_when_clear_size_changes",
        "invalid_marker_order": "test_fails_when_marker_order_changes",
        "invalid_marker_ownership": "test_fails_when_marker_owner_is_missing",
        "invalid_failure_status": "test_fails_when_failure_status_changes",
        "invalid_halt_behavior": "test_fails_when_terminal_halt_is_not_authoritative",
        "missing_non_goal": "test_fails_when_general_copy_non_goal_is_missing",
        "claim_boundary_too_broad": "test_fails_when_hostile_code_boundary_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserRequestBoundaryContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        self.assertEqual(self.validate_fixture().status, "pass")
        self.assertEqual(self.validate_fixture().code, OK)

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

    def test_fails_when_boundary_returns_to_ring3(self):
        result = self.validate_fixture(mutate=self.nested("execution_point", "returns_to_ring3", False))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_execution_point")

    def test_fails_when_request_payload_changes(self):
        result = self.validate_fixture(mutate=self.nested("request", "payload", "0x1"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_request_geometry")

    def test_fails_when_response_layout_changes(self):
        def mutation(data):
            data["response"]["fields"][0]["offset"] = 4
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_response_geometry")

    def test_fails_when_response_exceeds_page(self):
        result = self.validate_fixture(
            mutate=self.nested("page_permissions", "page_end", "0x0000400000001090")
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_user_span")

    def test_fails_when_shadow_size_changes(self):
        result = self.validate_fixture(mutate=self.shadow("request", "size_bytes", 32))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_shadow_geometry")

    def test_fails_when_shadow_is_user_accessible(self):
        result = self.validate_fixture(mutate=self.nested("kernel_shadows", "user_accessible", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_shadow_policy")

    def test_fails_when_service_identifier_changes(self):
        result = self.validate_fixture(mutate=self.nested("fixed_service", "request_identifier", 2))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_service_identity")

    def test_fails_when_response_mask_changes(self):
        result = self.validate_fixture(mutate=self.nested("fixed_service", "response_token_mask", "0x1"))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_response_token_rule")

    def test_fails_when_service_reads_user_memory(self):
        result = self.validate_fixture(mutate=self.nested("fixed_service", "reads_user_memory", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "service_crosses_copy_boundary")

    def test_fails_when_frame_validation_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("copy_boundary", "saved_frame_validation_before_copy_in", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_copy_requirement")

    def test_fails_when_user_pointer_is_allowed(self):
        result = self.validate_fixture(mutate=self.nested("copy_boundary", "user_supplied_pointer", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "caller_controlled_copy")

    def test_fails_when_copy_size_changes(self):
        result = self.validate_fixture(mutate=self.nested("copy_boundary", "copy_in_size_bytes", 32))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_copy_size")

    def test_fails_when_page_becomes_executable(self):
        result = self.validate_fixture(mutate=self.nested("page_permissions", "executable", True))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_page_policy")

    def test_fails_when_post_copy_clear_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("buffer_clearing", "response_clear_after_copy_out_validation", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_buffer_clear")

    def test_fails_when_zero_readback_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("buffer_clearing", "zero_readback_required", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "missing_buffer_clear_readback")

    def test_fails_when_clear_size_changes(self):
        result = self.validate_fixture(
            mutate=self.nested("buffer_clearing", "user_request_clear_size_bytes", 32)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_clear_size")

    def test_fails_when_marker_order_changes(self):
        mutation = lambda data: data | {"marker_order": list(reversed(data["marker_order"]))}
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_marker_order")

    def test_fails_when_marker_owner_is_missing(self):
        def mutation(data):
            del data["marker_ownership"]["KOZO_FIXED_USER_REQUEST_OK"]
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_marker_ownership")

    def test_fails_when_failure_status_changes(self):
        result = self.validate_fixture(mutate=self.nested("failure_statuses", "range_invalid", 99))
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_failure_status")

    def test_fails_when_terminal_halt_is_not_authoritative(self):
        result = self.validate_fixture(
            mutate=self.nested("halt_behavior", "terminal_halt_remains_authoritative", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_reason(result, "invalid_halt_behavior")

    def test_fails_when_general_copy_non_goal_is_missing(self):
        mutation = lambda data: data | {"non_goals": [value for value in data["non_goals"] if value != "general copy_from_user"]}
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
        result = self.validate_fixture(mutate=self.nested("fixed_service", "request_identifier", 2))
        self.assertEqual(result.code, FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def nested(self, section, field, value):
        return lambda data: mutate_nested(data, section, field, value)

    def shadow(self, name, field, value):
        def mutation(data):
            data["kernel_shadows"][name][field] = value
            return data
        return mutation

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_REQUEST_BOUNDARY_CONTRACT_INVALID)
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
                return FixedUserRequestBoundaryContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original


def mutate_nested(data, section, field, value):
    data[section][field] = value
    return data


if __name__ == "__main__":
    unittest.main()
