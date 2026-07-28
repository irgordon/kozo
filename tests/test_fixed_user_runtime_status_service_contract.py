from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import fixed_user_runtime_status_service_contract as contract_module
from harness.codes import FIXED_USER_RUNTIME_STATUS_SERVICE_CONTRACT_INVALID, OK
from harness.validators_impl import fixed_user_runtime_status_service_contract as validator_module
from harness.validators_impl.fixed_user_runtime_status_service_contract import (
    FixedUserRuntimeStatusServiceContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_runtime_status_service_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_is_invalid",
        "runtime_order_invalid": "test_fails_when_boot_executes_transaction",
        "shared_status_invalid": "test_fails_when_snapshot_is_user_accessible",
        "snapshot_geometry_invalid": "test_fails_when_snapshot_layout_changes",
        "snapshot_values_invalid": "test_fails_when_planned_stage_is_reported",
        "request_identity_invalid": "test_fails_when_request_id_changes",
        "response_geometry_invalid": "test_fails_when_response_size_changes",
        "feature_mask_invalid": "test_fails_when_feature_bit_is_duplicated",
        "ring3_validation_invalid": "test_fails_when_ring3_field_validation_is_partial",
        "ring0_revalidation_invalid": "test_fails_when_ring0_digest_validation_is_optional",
        "cleanup_invalid": "test_fails_when_snapshot_clear_is_optional",
        "marker_order_invalid": "test_fails_when_marker_order_changes",
        "failure_behavior_invalid": "test_fails_when_capability_can_follow_failure",
        "missing_claim_boundary": "test_fails_when_claim_boundary_is_empty",
        "missing_non_goal": "test_fails_when_public_syscall_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserRuntimeStatusServiceContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_response_digest_uses_all_eleven_qwords(self):
        self.assertEqual(contract_module.response_digest(tuple(range(11))), 11)
        with self.assertRaises(ValueError):
            contract_module.response_digest((1, 2))

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove=True)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file")

    def test_fails_when_json_is_invalid(self):
        result = self.validate_fixture(text="{bad")
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json")

    def test_fails_when_schema_is_invalid(self):
        result = self.validate_fixture(mutate=lambda value: value | {"version": 1})
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation")

    def test_fails_when_boot_executes_transaction(self):
        result = self.validate_fixture(
            mutate=self.nested("runtime_ordering", "boot_executes_transaction", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "runtime_order_invalid")

    def test_fails_when_snapshot_is_user_accessible(self):
        result = self.validate_fixture(
            mutate=self.nested("shared_status", "user_accessible", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "shared_status_invalid")

    def test_fails_when_snapshot_layout_changes(self):
        def mutation(value):
            value["shared_status"]["fields"][0]["offset"] = 8
            return value

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "snapshot_geometry_invalid")

    def test_fails_when_planned_stage_is_reported(self):
        def mutation(value):
            value["shared_status"]["expected_values"]["current_runtime_stage"] = 6
            return value

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "snapshot_values_invalid")

    def test_fails_when_request_id_changes(self):
        result = self.validate_fixture(
            mutate=self.nested("request", "identifier", 3)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "request_identity_invalid")

    def test_fails_when_response_size_changes(self):
        result = self.validate_fixture(
            mutate=self.nested("response", "size_bytes", 96)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "response_geometry_invalid")

    def test_fails_when_feature_bit_is_duplicated(self):
        def mutation(value):
            value["feature_mask_bits"][6]["bit"] = 5
            return value

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "feature_mask_invalid")

    def test_fails_when_feature_name_changes(self):
        def mutation(value):
            value["feature_mask_bits"][6]["name"] = "unknown_feature"
            return value

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "feature_mask_invalid")

    def test_fails_when_ring3_field_validation_is_partial(self):
        result = self.validate_fixture(
            mutate=self.nested(
                "ring3_validation",
                "all_response_fields_required",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "ring3_validation_invalid")

    def test_fails_when_ring0_digest_validation_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested(
                "ring0_revalidation",
                "digest_revalidation_required",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "ring0_revalidation_invalid")

    def test_fails_when_snapshot_clear_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested(
                "cleanup",
                "snapshot_cleared_after_internal_capability_1",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "cleanup_invalid")

    def test_fails_when_marker_order_changes(self):
        result = self.validate_fixture(
            mutate=lambda value: value
            | {"marker_order": list(reversed(value["marker_order"]))}
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "marker_order_invalid")

    def test_fails_when_capability_can_follow_failure(self):
        result = self.validate_fixture(
            mutate=self.nested(
                "failure_behavior",
                "internal_capabilities_forbidden_after_transaction_failure",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "failure_behavior_invalid")

    def test_fails_when_claim_boundary_is_empty(self):
        result = self.validate_fixture(
            mutate=self.nested("claim_boundary", "proves", [])
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_claim_boundary")

    def test_fails_when_public_syscall_non_goal_is_missing(self):
        def mutation(value):
            value["non_goals"].remove("public syscall ABI")
            return value

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate=self.nested("request", "identifier", 3)
        )
        self.assertEqual(
            result.code,
            FIXED_USER_RUNTIME_STATUS_SERVICE_CONTRACT_INVALID,
        )
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def nested(self, section, field, value):
        def mutation(document):
            document[section][field] = value
            return document

        return mutation

    def validate_fixture(self, *, mutate=None, text=None, remove=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            if not remove:
                value = json.loads(validator_module._CONTRACT_PATH.read_text())
                if mutate is not None:
                    value = mutate(copy.deepcopy(value))
                path.write_text(text if text is not None else json.dumps(value))
            original = validator_module._CONTRACT_PATH
            validator_module._CONTRACT_PATH = path
            try:
                return FixedUserRuntimeStatusServiceContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def assert_failure(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(
            result.code,
            FIXED_USER_RUNTIME_STATUS_SERVICE_CONTRACT_INVALID,
        )
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)


if __name__ == "__main__":
    unittest.main()
