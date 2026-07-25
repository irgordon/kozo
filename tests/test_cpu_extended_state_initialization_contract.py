from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import CPU_EXTENDED_STATE_INITIALIZATION_CONTRACT_INVALID, OK
from harness.validators_impl import cpu_extended_state_initialization_contract as validator_module
from harness.validators_impl.cpu_extended_state_initialization_contract import (
    CpuExtendedStateInitializationContractValidator,
)

KOZO_NEGATIVE_COVERAGE = {
    "cpu_extended_state_initialization_contract": {
        "missing_contract_file": "test_fails_when_contract_is_missing",
        "invalid_contract_json": "test_fails_when_contract_json_is_invalid",
        "contract_schema_violation": "test_fails_when_schema_is_violated",
        "missing_required_cpu_feature": "test_fails_when_required_cpu_feature_is_missing",
        "invalid_control_policy": "test_fails_when_cr0_policy_is_wrong",
        "osxsave_permitted": "test_fails_when_osxsave_is_permitted",
        "invalid_x87_policy": "test_fails_when_x87_control_word_is_wrong",
        "invalid_sse_policy": "test_fails_when_mxcsr_is_wrong",
        "invalid_probe_geometry": "test_fails_when_probe_geometry_is_wrong",
        "wrong_marker_order": "test_fails_when_marker_order_is_wrong",
        "avx_not_prohibited": "test_fails_when_avx_prohibition_is_missing",
        "missing_non_goal": "test_fails_when_non_goal_is_missing",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class CpuExtendedStateInitializationContractValidatorTests(unittest.TestCase):
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

    def test_fails_when_schema_is_violated(self):
        result = self.validate_fixture(lambda value: value | {"version": 1})

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "contract_schema_violation", "contract")

    def test_fails_when_required_cpu_feature_is_missing(self):
        result = self.validate_fixture(remove_named_bit("required_cpu_features", "required_bits", "SSE2"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_required_cpu_feature", "required_cpu_features.required_bits")

    def test_fails_when_cr0_policy_is_wrong(self):
        result = self.validate_fixture(replace_named_bit("cr0_policy", "required_set_bits", "MP", bit=2))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_control_policy", "cr0_policy.required_set_bits")

    def test_fails_when_osxsave_is_permitted(self):
        result = self.validate_fixture(replace_section("avx_prohibition", cr4_osxsave_required_value=1))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "avx_not_prohibited", "avx_prohibition.cr4_osxsave_required_value")

    def test_fails_when_x87_control_word_is_wrong(self):
        result = self.validate_fixture(replace_section("x87_initialization", expected_control_word="0x027f"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_x87_policy", "x87_initialization.expected_control_word")

    def test_fails_when_mxcsr_is_wrong(self):
        result = self.validate_fixture(replace_section("sse_initialization", expected_mxcsr="0x00000000"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_sse_policy", "sse_initialization.expected_mxcsr")

    def test_fails_when_probe_geometry_is_wrong(self):
        result = self.validate_fixture(replace_section("simd_probe", buffer_alignment_bytes=8))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "invalid_probe_geometry", "simd_probe.buffer_alignment_bytes")

    def test_fails_when_marker_order_is_wrong(self):
        def mutate(value):
            markers = list(value["success_markers"])
            markers[1], markers[2] = markers[2], markers[1]
            return value | {"success_markers": markers}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "wrong_marker_order", "success_markers")

    def test_fails_when_avx_prohibition_is_missing(self):
        def mutate(value):
            policy = value["avx_prohibition"] | {"forbidden_register_classes": ["ymm"]}
            return value | {"avx_prohibition": policy}

        result = self.validate_fixture(mutate)

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "avx_not_prohibited", "avx_prohibition.forbidden_register_classes")

    def test_fails_when_non_goal_is_missing(self):
        result = self.validate_fixture(remove_value("non_goals", "production readiness"))

        self.assertEqual(result.status, "fail")
        self.assert_failure(result, "missing_non_goal", "non_goals.production readiness")

    def test_failure_diagnostic_names_field(self):
        result = self.validate_fixture(replace_named_bit("cr0_policy", "required_set_bits", "MP", bit=2))

        self.assertEqual(result.status, "fail")
        self.assertIn("reason", result.meta)
        self.assertIn("contract_field", result.meta)

    def validate_fixture(self, mutate=None, *, remove_contract=False, contract_text=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            if not remove_contract:
                value = json.loads(validator_module._CONTRACT_PATH.read_text())
                value = mutate(value) if mutate else value
                path.write_text(contract_text if contract_text is not None else json.dumps(value))
            original = validator_module._CONTRACT_PATH
            validator_module._CONTRACT_PATH = path
            try:
                return CpuExtendedStateInitializationContractValidator().validate({})
            finally:
                validator_module._CONTRACT_PATH = original

    def assert_failure(self, result, reason, field):
        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, CPU_EXTENDED_STATE_INITIALIZATION_CONTRACT_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], field)


def replace_section(section, **updates):
    return lambda value: value | {section: value[section] | updates}


def remove_named_bit(section, field, name):
    def mutate(value):
        values = [item for item in value[section][field] if item["name"] != name]
        return value | {section: value[section] | {field: values}}

    return mutate


def replace_named_bit(section, field, name, **updates):
    def mutate(value):
        values = [item | updates if item["name"] == name else item for item in value[section][field]]
        return value | {section: value[section] | {field: values}}

    return mutate


def remove_value(section, target):
    return lambda value: value | {section: [item for item in value[section] if item != target]}


if __name__ == "__main__":
    unittest.main()
