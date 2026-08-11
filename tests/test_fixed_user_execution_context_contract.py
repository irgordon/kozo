from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import fixed_user_execution_context_contract as contract_module
from harness.codes import FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID, OK
from harness.validators_impl import fixed_user_execution_context_contract as validator_module
from harness.validators_impl.fixed_user_execution_context_contract import (
    FixedUserExecutionContextContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_execution_context_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_rejects_unknown_field",
        "invalid_authority": "test_fails_when_identity_is_user_selectable",
        "invalid_context_geometry": "test_fails_when_context_size_changes",
        "invalid_identity": "test_fails_when_zero_identity_is_allowed_while_live",
        "invalid_reserved_state": "test_fails_when_reserved_field_is_nonzero",
        "invalid_lifecycle": "test_fails_when_success_transition_is_skipped",
        "invalid_cleanup_edge": "test_fails_when_active_cleanup_edge_is_missing",
        "invalid_clear_state": "test_fails_when_identity_is_not_cleared",
        "invalid_result_geometry": "test_fails_when_result_contains_identity",
        "result_retains_authority": "test_result_authority_fields_are_forbidden",
        "invalid_result_lifetime": "test_fails_when_stale_result_may_be_reused",
        "invalid_binding": "test_fails_when_fixed_code_binding_changes",
        "binding_source_mismatch": "test_fails_when_stack_binding_differs_from_source_contract",
        "invalid_transition_budget": "test_fails_when_budget_is_not_two",
        "invalid_phase_count_coupling": "test_fails_when_correct_phase_has_wrong_count",
        "third_transition_allowed": "test_fails_when_third_transition_is_allowed",
        "invalid_progression": "test_fails_when_odin_continuation_precedes_clear",
        "implementation_overclaim": "test_fails_when_implementation_is_authorized",
        "evidence_count_changed": "test_fails_when_marker_count_changes",
        "runtime_evidence_overclaim": "test_fails_when_runtime_evidence_is_claimed",
        "portability_weakened": "test_fails_when_windows_build_host_is_removed",
        "diagnostic_names_field": "test_failure_diagnostic_names_contract_field",
    }
}


class FixedUserExecutionContextContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_contract_is_missing(self):
        self.assert_reason(self.validate_fixture(remove=True), "missing_contract_file")

    def test_fails_when_contract_json_is_invalid(self):
        self.assert_reason(self.validate_fixture(text="{bad"), "invalid_contract_json")

    def test_fails_when_schema_rejects_unknown_field(self):
        self.assert_reason(self.validate_fixture(mutate=lambda data: data | {"unknown": 1}), "contract_schema_violation")

    def test_fails_when_contract_version_changes(self):
        self.assert_reason(self.validate_fixture(mutate=self.set_path("version", value=1)), "contract_schema_violation")

    def test_fails_when_identity_is_user_selectable(self):
        mutation = self.set_path("authority", "user_selectable_identity", value=True)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_context_size_changes(self):
        mutation = self.set_path("context", "size_bytes", value=120)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_required_context_field_is_missing(self):
        def mutation(data):
            data["context"]["fields"].pop()
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_zero_identity_is_allowed_while_live(self):
        mutation = self.mutate_field("context", "opaque_identity", "allowed", "zero")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_identity")

    def test_fails_when_reserved_field_is_nonzero(self):
        mutation = self.mutate_field("context", "reserved_0", "cleared", 1)
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_reserved_state")

    def test_successful_lifecycle_graph_is_exact(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        for from_state, to_state in (("UNINITIALIZED", "READY"), ("READY", "ACTIVE"), ("ACTIVE", "RETURNED"), ("RETURNED", "CLEARED")):
            self.assertTrue(contract_module.transition_is_allowed(contract, from_state, to_state))

    def test_active_is_allowed_only_from_ready(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertTrue(contract_module.transition_is_allowed(contract, "READY", "ACTIVE"))
        self.assertFalse(contract_module.transition_is_allowed(contract, "UNINITIALIZED", "ACTIVE"))
        self.assertFalse(contract_module.transition_is_allowed(contract, "CLEARED", "ACTIVE"))

    def test_returned_requires_active_completion(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertTrue(contract_module.transition_is_allowed(contract, "ACTIVE", "RETURNED"))
        self.assertFalse(contract_module.transition_is_allowed(contract, "READY", "RETURNED"))

    def test_terminal_success_requires_cleanup_to_cleared(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertTrue(contract_module.transition_is_allowed(contract, "RETURNED", "CLEARED"))

    def test_fails_when_success_transition_is_skipped(self):
        mutation = self.set_path("lifecycle", "successful_transitions", 1, "to", value="RETURNED")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_lifecycle")

    def test_fails_when_backward_transition_is_added(self):
        mutation = self.set_path("lifecycle", "successful_transitions", 2, "to", value="READY")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_lifecycle")

    def test_fails_when_cleared_can_become_active(self):
        def mutation(data):
            data["lifecycle"]["successful_transitions"].append({"from": "CLEARED", "to": "ACTIVE"})
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_lifecycle")

    def test_fails_when_forbidden_transition_is_removed(self):
        def mutation(data):
            data["lifecycle"]["forbidden_transitions"].pop()
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_pre_ready_failure_can_enter_ring3(self):
        mutation = self.set_path("lifecycle", "pre_ready_failure", value="enter_ring3")
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_lifecycle_encoding_is_unsupported(self):
        mutation = self.set_path("lifecycle", "encodings", "ACTIVE", value=9)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_active_cleanup_edge_is_missing(self):
        def mutation(data):
            data["lifecycle"]["failure_cleanup_transitions"].pop(1)
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_cleanup_edge")

    def test_fails_when_identity_is_not_cleared(self):
        def mutation(data):
            data["clear_state"]["zeroized_fields"].remove("opaque_identity")
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_clear_state")

    def test_valid_result_is_separate_and_non_authoritative(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertEqual(contract.result["outcomes"]["SUCCESS"], 1)
        self.assertFalse(contract.result_lifetime["can_authorize_execution"])
        self.assertNotIn("opaque_identity", contract_module.result_field_names(contract))

    def test_result_defines_success_and_named_failure(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertEqual(contract.result["outcomes"], {"INITIAL": 0, "SUCCESS": 1, "FAILURE": 2})
        self.assertEqual(contract.result["failure_codes"]["CLEANUP_FAILED"], 11)

    def test_result_preserves_transition_count_without_authority(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertIn("observed_transition_count", contract_module.result_field_names(contract))
        self.assertTrue(contract.result_lifetime["survives_context_clear"])
        self.assertFalse(contract.result_lifetime["can_authorize_execution"])

    def test_fails_when_result_contains_identity(self):
        mutation = self.set_path("result", "fields", 6, "name", value="opaque_identity")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_result_geometry")

    def test_result_authority_fields_are_forbidden(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        forbidden = set(contract.result["authority_fields_forbidden"])
        self.assertIn("kernel_pointer", forbidden)
        self.assertIn("selector", forbidden)
        self.assertIn("reusable_handle", forbidden)

    def test_fails_when_result_authority_exclusion_is_removed(self):
        def mutation(data):
            data["result"]["authority_fields_forbidden"].remove("kernel_pointer")
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "result_retains_authority")

    def test_fails_when_named_failure_is_removed(self):
        def mutation(data):
            del data["result"]["failure_codes"]["INVALID_RETURN_STATE"]
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_stale_result_may_be_reused(self):
        mutation = self.set_path("result_lifetime", "reset_before_future_initialization", value=False)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_fixed_code_binding_changes(self):
        mutation = self.set_path("fixed_bindings", "user_code", "virtual_start", value="0x0000400000001000")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_binding")

    def test_fails_when_stack_binding_differs_from_source_contract(self):
        mutation = self.set_path("fixed_bindings", "user_stack", "initial_rsp", value="0x0000400000002fe0")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_binding")

    def test_transition_budget_is_derived_from_current_authority(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertEqual(contract.transition_budget["authorized_count"], 2)
        self.assertTrue(contract_module.transition_phase_matches(contract, "REQUEST_PENDING", 0))
        self.assertTrue(contract_module.transition_phase_matches(contract, "RESPONSE_READY", 1))
        self.assertTrue(contract_module.transition_phase_matches(contract, "CONSUMED", 2))

    def test_transition_count_above_budget_is_rejected(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertFalse(contract_module.transition_phase_matches(contract, "CONSUMED", 3))

    def test_unknown_lifecycle_transition_is_rejected(self):
        contract = contract_module.load_fixed_user_execution_context_contract()
        self.assertFalse(contract_module.transition_is_allowed(contract, "UNKNOWN", "ACTIVE"))

    def test_nested_binding_unknown_field_is_rejected(self):
        def mutation(data):
            data["fixed_bindings"]["user_code"]["unknown"] = 1
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_budget_is_not_two(self):
        mutation = self.set_path("transition_budget", "authorized_count", value=3)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_correct_phase_has_wrong_count(self):
        mutation = self.set_path("transition_budget", "derivation", 1, "required_count_before", value=0)
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_phase_count_coupling")

    def test_fails_when_correct_count_has_wrong_phase(self):
        mutation = self.set_path("transition_budget", "derivation", 1, "required_phase_before", value="REQUEST_PENDING")
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_phase_count_coupling")

    def test_fails_when_third_transition_is_allowed(self):
        mutation = self.set_path("transition_budget", "third_transition", value="accepted")
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_current_transaction_has_both_governed_return_sites(self):
        source = (contract_module.CONTRACT_PATH.parents[1] / "kernel/arch/x86_64/privilege_transition.asm").read_text()
        self.assertIn("int KOZO_PRIVILEGE_RETURN_VECTOR\nuser_privilege_probe_after_interrupt:", source)
        self.assertIn("int KOZO_PRIVILEGE_RETURN_VECTOR\nuser_response_consumer_interrupt_return:", source)

    def test_fails_when_odin_continuation_precedes_clear(self):
        def mutation(data):
            placement = data["runtime_progression"]["placement"]
            continuation = placement.pop()
            placement.insert(1, continuation)
            return data
        self.assert_reason(self.validate_fixture(mutate=mutation), "invalid_progression")

    def test_fails_when_implementation_is_authorized(self):
        mutation = self.set_path("runtime_progression", "implementation_authorized", value=True)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_marker_count_changes(self):
        mutation = self.set_path("evidence_policy", "marker_count", value=42)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_runtime_evidence_is_claimed(self):
        mutation = self.set_path("evidence_policy", "runtime_evidence_claimed", value=True)
        self.assert_reason(self.validate_fixture(mutate=mutation), "contract_schema_violation")

    def test_fails_when_windows_build_host_is_removed(self):
        mutation = self.set_path("evidence_policy", "required_build_hosts", value=["ubuntu-24.04", "macos-15"])
        self.assert_reason(self.validate_fixture(mutate=mutation), "portability_weakened")

    def test_failure_diagnostic_names_contract_field(self):
        result = self.validate_fixture(mutate=self.set_path("fixed_bindings", "user_code", "size_bytes", value=8192))
        self.assertEqual(result.code, FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID)
        self.assertIn("reason", result.meta)
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
                return FixedUserExecutionContextContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def set_path(self, *path, value):
        def mutation(data):
            target = data
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            return data
        return mutation

    def mutate_field(self, section, field_name, key, value):
        def mutation(data):
            field = next(item for item in data[section]["fields"] if item["name"] == field_name)
            field[key] = value
            return data
        return mutation

    def assert_reason(self, result, reason):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_EXECUTION_CONTEXT_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)


if __name__ == "__main__":
    unittest.main()
