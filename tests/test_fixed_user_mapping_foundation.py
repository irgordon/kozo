from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import fixed_user_mapping_foundation as contract_module
from harness.codes import FIXED_USER_MAPPING_FOUNDATION_INVALID, OK
from harness.validators_impl import fixed_user_mapping_foundation as validator_module
from harness.validators_impl.fixed_user_mapping_foundation import (
    FixedUserMappingFoundationValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "fixed_user_mapping_foundation": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_contract_schema_is_violated",
        "invalid_page_size": "test_fails_when_page_size_is_invalid",
        "invalid_table_geometry": "test_fails_when_table_geometry_is_invalid",
        "kernel_user_accessible": "test_fails_when_kernel_region_is_user_accessible",
        "write_execute_violation": "test_fails_when_kernel_region_is_writable_and_executable",
        "noncanonical_virtual_address": "test_fails_when_user_address_is_noncanonical",
        "misaligned_backing": "test_fails_when_user_backing_is_misaligned",
        "overlapping_user_regions": "test_fails_when_user_regions_overlap",
        "invalid_user_permissions": "test_fails_when_user_code_is_writable",
        "missing_user_propagation": "test_fails_when_upper_level_user_propagation_is_missing",
        "missing_wx_rule": "test_fails_when_write_xor_execute_rule_is_missing",
        "invalid_activation_policy": "test_fails_when_cr3_readback_is_optional",
        "missing_software_walk": "test_fails_when_software_walk_is_missing",
        "missing_survival_requirement": "test_fails_when_survival_restore_is_missing",
        "invalid_marker_order": "test_fails_when_marker_order_is_invalid",
        "missing_non_goal": "test_fails_when_ring3_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class FixedUserMappingFoundationValidatorTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_contract_is_missing(self):
        result = self.validate_fixture(remove_contract=True)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_contract_file", "contract")

    def test_fails_when_contract_json_is_invalid(self):
        result = self.validate_fixture(mutate_text=lambda _: "{invalid")
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_contract_json", "contract")

    def test_fails_when_contract_schema_is_violated(self):
        result = self.validate_fixture(mutate=lambda data: data | {"version": 1})
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_page_size_is_invalid(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(data, "paging", "page_size_bytes", 8192)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_page_size", "paging")

    def test_fails_when_table_geometry_is_invalid(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(data, "page_tables", "page_count", 6)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_table_geometry", "page_tables")

    def test_fails_when_kernel_region_is_user_accessible(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(data, "kernel_regions", "kernel_text", "user", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "kernel_user_accessible", "kernel_regions.user")

    def test_fails_when_kernel_region_is_writable_and_executable(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(data, "kernel_regions", "kernel_text", "writable", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "write_execute_violation", "kernel_regions")

    def test_fails_when_user_address_is_noncanonical(self):
        def mutation(data):
            result = mutate_region(
                data,
                "user_regions",
                "user_probe_code",
                "virtual_start",
                "0x0000800000000000",
            )
            return mutate_region(
                result,
                "user_regions",
                "user_probe_code",
                "virtual_end",
                "0x0000800000001000",
            )

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "noncanonical_virtual_address", "user_regions.user_probe_code")

    def test_fails_when_user_backing_is_misaligned(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(
                data,
                "user_regions",
                "user_probe_data",
                "virtual_end",
                "0x0000400000002001",
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "misaligned_backing", "user_regions.user_probe_data")

    def test_fails_when_user_regions_overlap(self):
        def mutation(data):
            result = mutate_region(
                data,
                "user_regions",
                "user_probe_data",
                "virtual_start",
                "0x0000400000000000",
            )
            return mutate_region(
                result,
                "user_regions",
                "user_probe_data",
                "virtual_end",
                "0x0000400000001000",
            )

        result = self.validate_fixture(mutate=mutation)
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "overlapping_user_regions", "user_regions")

    def test_fails_when_user_code_is_writable(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(data, "user_regions", "user_probe_code", "writable", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_user_permissions", "user_regions.user_probe_code")

    def test_fails_when_user_data_is_executable(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(data, "user_regions", "user_probe_data", "executable", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_user_permissions", "user_regions.user_probe_data")

    def test_fails_when_user_stack_is_executable(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_region(data, "user_regions", "user_probe_stack", "executable", True)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_user_permissions", "user_regions.user_probe_stack")

    def test_fails_when_upper_level_user_propagation_is_missing(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(
                data,
                "permission_policy",
                "user_levels",
                ["PDPTE", "PDE", "PTE"],
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_user_propagation", "permission_policy.user_levels")

    def test_fails_when_write_xor_execute_rule_is_missing(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(
                data,
                "permission_policy",
                "write_xor_execute_required",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_wx_rule", "permission_policy")

    def test_fails_when_cr3_readback_is_optional(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(data, "activation", "readback_required", False)
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_activation_policy", "activation")

    def test_fails_when_software_walk_is_missing(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(data, "software_walk", "symbol", "missing_walk")
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_software_walk", "software_walk")

    def test_fails_when_survival_restore_is_missing(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(
                data,
                "survival_probe",
                "user_data_write_read_restore",
                False,
            )
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_survival_requirement", "survival_probe")

    def test_fails_when_marker_order_is_invalid(self):
        result = self.validate_fixture(
            mutate=lambda data: data | {"success_markers": list(reversed(data["success_markers"]))}
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_marker_order", "success_markers")

    def test_fails_when_ring3_non_goal_is_missing(self):
        result = self.validate_fixture(
            mutate=lambda data: data | {
                "non_goals": [value for value in data["non_goals"] if value != "Ring 3 execution"]
            }
        )
        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.Ring 3 execution")

    def test_effective_permissions_require_user_bit_at_every_level(self):
        user_entries = [0x7, 0x7, 0x7, 0x7]
        for missing_level in range(4):
            entries = list(user_entries)
            entries[missing_level] &= ~contract_module.USER
            permissions = contract_module.effective_page_permissions(entries)
            self.assertFalse(permissions.user_accessible)

    def test_effective_permissions_combine_write_and_nx(self):
        code = contract_module.effective_page_permissions([0x7, 0x7, 0x7, 0x5])
        data = contract_module.effective_page_permissions(
            [0x7, 0x7, 0x7, contract_module.NX | 0x7]
        )

        self.assertFalse(code.writable)
        self.assertTrue(code.executable)
        self.assertTrue(data.writable)
        self.assertFalse(data.executable)

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(
            mutate=lambda data: mutate_nested(data, "activation", "readback_required", False)
        )

        self.assertEqual(result.code, FIXED_USER_MAPPING_FOUNDATION_INVALID)
        self.assertEqual(result.meta["reason"], "invalid_activation_policy")
        self.assertEqual(result.meta["contract_field"], "activation")

    def validate_fixture(self, *, remove_contract=False, mutate=None, mutate_text=None):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "fixed_user_mapping_foundation.v0.json"
            path.write_text(contract_module.CONTRACT_PATH.read_text())
            if remove_contract:
                path.unlink()
            elif mutate_text is not None:
                path.write_text(mutate_text(path.read_text()))
            elif mutate is not None:
                data = json.loads(path.read_text())
                path.write_text(json.dumps(mutate(data), indent=2) + "\n")
            original_contract = validator_module._CONTRACT_PATH
            validator_module._CONTRACT_PATH = path
            try:
                return FixedUserMappingFoundationValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original_contract

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, FIXED_USER_MAPPING_FOUNDATION_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def mutate_nested(data, section, field, value):
    result = copy.deepcopy(data)
    result[section][field] = value
    return result


def mutate_region(data, section, name, field, value):
    result = copy.deepcopy(data)
    for region in result[section]:
        if region["name"] == name:
            region[field] = value
            return result
    raise AssertionError(f"Missing region: {name}")


if __name__ == "__main__":
    unittest.main()
