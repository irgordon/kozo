from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID, OK
from harness.validators_impl import bounded_privilege_transition_probe_contract as validator_module
from harness.validators_impl.bounded_privilege_transition_probe_contract import (
    BoundedPrivilegeTransitionProbeContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "bounded_privilege_transition_probe_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_is_invalid",
        "invalid_transition_mechanism": "test_fails_when_transition_mechanism_is_invalid",
        "invalid_selector": "test_fails_when_user_selector_is_invalid",
        "invalid_gdt_geometry": "test_fails_when_gdt_geometry_is_invalid",
        "invalid_tss_geometry": "test_fails_when_tss_geometry_is_invalid",
        "invalid_tss_rsp0": "test_fails_when_tss_rsp0_is_invalid",
        "invalid_return_gate": "test_fails_when_return_gate_is_invalid",
        "invalid_stack_geometry": "test_fails_when_return_stack_geometry_is_invalid",
        "invalid_stack_permissions": "test_fails_when_return_stack_is_user_accessible",
        "invalid_user_rsp": "test_fails_when_user_rsp_is_invalid",
        "invalid_user_rip": "test_fails_when_user_rip_is_invalid",
        "missing_cpl_validation": "test_fails_when_cpl_validation_is_missing",
        "invalid_rflags_policy": "test_fails_when_rflags_policy_is_invalid",
        "invalid_user_code_permissions": "test_fails_when_user_code_is_writable",
        "invalid_probe_width": "test_fails_when_probe_width_is_invalid",
        "missing_probe_requirement": "test_fails_when_probe_clear_is_optional",
        "invalid_return_boundary": "test_fails_when_user_return_is_allowed",
        "invalid_return_target": "test_fails_when_return_target_is_dynamic",
        "invalid_marker_order": "test_fails_when_marker_order_is_invalid",
        "invalid_failure_status": "test_fails_when_failure_status_changes",
        "missing_non_goal": "test_fails_when_userspace_non_goal_is_missing",
        "claim_boundary_too_broad": "test_fails_when_claim_boundary_is_too_broad",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class BoundedPrivilegeTransitionProbeContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove=True)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(text="{bad")
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_schema_is_invalid(self):
        result = self.validate_fixture(mutate=lambda data: data | {"version": 1})
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_transition_mechanism_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("transition", "entry_mechanism", "syscall"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_transition_mechanism")

    def test_fails_when_user_selector_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("selectors", "user_code", "0x2b"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_selector")

    def test_fails_when_gdt_geometry_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("gdt", "size_bytes", 64))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_gdt_geometry")

    def test_fails_when_tss_geometry_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("tss", "size_bytes", 112))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_tss_geometry")

    def test_fails_when_tss_rsp0_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("tss", "rsp0_symbol", "boot_stack_top"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_tss_rsp0")

    def test_fails_when_return_gate_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("idt", "return_gate_dpl", 0))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_return_gate")

    def test_fails_when_return_stack_geometry_is_invalid(self):
        result = self.validate_fixture(mutate=self.stack("return", "size_bytes", 2048))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_stack_geometry")

    def test_fails_when_return_stack_is_user_accessible(self):
        result = self.validate_fixture(mutate=self.stack("return", "user", True))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_stack_permissions")

    def test_fails_when_user_rsp_is_invalid(self):
        result = self.validate_fixture(mutate=self.stack("user", "initial_rsp", "0x0000400000003000"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_user_rsp")

    def test_fails_when_user_rip_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("entry", "fixed_virtual_rip", "0x1000"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_user_rip")

    def test_fails_when_cpl_validation_is_missing(self):
        result = self.validate_fixture(mutate=self.nested("entry", "cpl_check_required", False))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_cpl_validation")

    def test_fails_when_rflags_policy_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("entry", "sanitized_rflags", "0x202"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_rflags_policy")

    def test_fails_when_user_code_is_writable(self):
        result = self.validate_fixture(mutate=self.nested("entry", "code_writable", True))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_user_code_permissions")

    def test_fails_when_probe_width_is_invalid(self):
        result = self.validate_fixture(mutate=self.nested("probe", "response_size_bytes", 48))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_probe_width")

    def test_fails_when_probe_clear_is_optional(self):
        result = self.validate_fixture(
            mutate=self.nested("probe", "transaction_clear_readback_required", False)
        )
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_probe_requirement")

    def test_fails_when_user_return_is_allowed(self):
        result = self.validate_fixture(mutate=self.nested("return_boundary", "user_return_forbidden", False))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_return_boundary")

    def test_fails_when_return_target_is_dynamic(self):
        result = self.validate_fixture(mutate=self.nested("return_boundary", "fixed_continuation_symbol", "dynamic_target"))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_return_target")

    def test_fails_when_marker_order_is_invalid(self):
        result = self.validate_fixture(mutate=lambda data: data | {"success_markers": list(reversed(data["success_markers"]))})
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_marker_order")

    def test_fails_when_failure_status_changes(self):
        result = self.validate_fixture(mutate=self.nested("failure_statuses", "gdt_invalid", 9))
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "invalid_failure_status")

    def test_fails_when_userspace_non_goal_is_missing(self):
        mutation = lambda data: data | {"non_goals": [value for value in data["non_goals"] if value != "general userspace execution"]}
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_non_goal")

    def test_fails_when_claim_boundary_is_too_broad(self):
        def mutation(data):
            data["claim_boundary"]["does_not_prove"].remove("general userspace execution")
            return data
        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "claim_boundary_too_broad")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(mutate=self.nested("selectors", "user_code", "0x2b"))
        self.assertEqual(result.code, BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID)
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def nested(self, section, field, value):
        return lambda data: mutate_nested(data, section, field, value)

    def stack(self, name, field, value):
        def mutation(data):
            data["stacks"][name][field] = value
            return data
        return mutation

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, BOUNDED_PRIVILEGE_TRANSITION_PROBE_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)

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
                return BoundedPrivilegeTransitionProbeContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original


def mutate_nested(data, section, field, value):
    data[section][field] = value
    return data


if __name__ == "__main__":
    unittest.main()
