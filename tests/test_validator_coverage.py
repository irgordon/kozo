from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import OK, VALIDATOR_COVERAGE_INVALID
from harness.validators_impl import validator_coverage
from harness.validators_impl.validator_coverage import (
    ValidatorCoverageValidator,
    ValidatorTestContract,
)

KOZO_NEGATIVE_COVERAGE = {
    "validator_coverage": {
        "missing_test_file": "test_fails_when_registered_validator_has_missing_test_file",
        "missing_coverage_mapping": "test_fails_when_registered_validator_has_missing_coverage_mapping",
        "missing_negative_test": "test_fails_when_test_file_has_missing_negative_test",
        "placeholder_negative_rejected": "test_fails_when_placeholder_has_token_and_negative_name_only",
        "missing_failure_assertion": "test_fails_when_negative_test_invokes_validator_without_failure_assertion",
        "missing_validator_invocation": "test_fails_when_negative_test_asserts_failure_without_validator_invocation",
        "token_outside_negative_test": "test_fails_when_token_exists_only_outside_negative_test",
        "missing_coverage_metadata": "test_fails_when_required_marker_metadata_is_missing",
        "missing_required_marker": "test_fails_when_required_marker_is_missing",
        "unknown_marker": "test_fails_when_metadata_contains_unknown_marker",
        "mapped_test_missing": "test_fails_when_marker_maps_to_missing_test_function",
        "mapped_test_placeholder": "test_fails_when_marker_maps_to_placeholder_test",
        "mapped_test_missing_failure_assertion": "test_fails_when_marker_maps_to_test_without_failure_assertion",
        "mapped_test_missing_validator_invocation": "test_fails_when_marker_maps_to_test_without_validator_invocation",
        "diagnostic_names_requirement": "test_failure_diagnostics_name_validator_marker_and_requirement",
    }
}


class ValidatorCoverageValidatorTests(unittest.TestCase):
    def test_passes_when_all_validators_have_negative_test_coverage(self):
        result = ValidatorCoverageValidator().validate({})

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_registered_validator_has_missing_test_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "test_schema.py"
            original_registered = validator_coverage.registered_validator_names
            original_contracts = validator_coverage.validator_coverage_contracts
            validator_coverage.registered_validator_names = lambda: ("schema",)
            validator_coverage.validator_coverage_contracts = lambda: (
                ValidatorTestContract("schema", missing_path, "SchemaValidator", ("missing_file",)),
            )
            try:
                result = ValidatorCoverageValidator().validate({})
            finally:
                validator_coverage.registered_validator_names = original_registered
                validator_coverage.validator_coverage_contracts = original_contracts

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, VALIDATOR_COVERAGE_INVALID)
        self.assertEqual(result.meta["reason"], "missing_test_file")
        self.assertEqual(result.meta["validator_name"], "schema")

    def test_fails_when_registered_validator_has_missing_coverage_mapping(self):
        original_registered = validator_coverage.registered_validator_names
        original_contracts = validator_coverage.validator_coverage_contracts
        validator_coverage.registered_validator_names = lambda: ("new_validator",)
        validator_coverage.validator_coverage_contracts = lambda: ()
        try:
            result = ValidatorCoverageValidator().validate({})
        finally:
            validator_coverage.registered_validator_names = original_registered
            validator_coverage.validator_coverage_contracts = original_contracts

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_coverage_mapping")
        self.assertEqual(result.meta["validator_name"], "new_validator")

    def test_fails_when_test_file_has_missing_negative_test(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_path = Path(temporary_directory) / "test_schema.py"
            test_path.write_text(
                "from harness.validators_impl.schema import SchemaValidator\n"
                "def test_pass_path():\n"
                "    SchemaValidator\n"
            )
            original_registered = validator_coverage.registered_validator_names
            original_contracts = validator_coverage.validator_coverage_contracts
            validator_coverage.registered_validator_names = lambda: ("schema",)
            validator_coverage.validator_coverage_contracts = lambda: (
                ValidatorTestContract("schema", test_path, "SchemaValidator", ("missing_negative",)),
            )
            try:
                result = ValidatorCoverageValidator().validate({})
            finally:
                validator_coverage.registered_validator_names = original_registered
                validator_coverage.validator_coverage_contracts = original_contracts

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_negative_test")
        self.assertEqual(result.meta["validator_name"], "schema")

    def test_fails_when_placeholder_has_token_and_negative_name_only(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("placeholder_negative",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'placeholder_negative': 'test_fails_placeholder'}}\n"
            "\n"
            "def test_fails_placeholder():\n"
            "    pass\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "negative_test_missing_validator_invocation")
        self.assertEqual(result.meta["validator_name"], "schema")

    def test_fails_when_negative_test_invokes_validator_without_failure_assertion(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("missing_failure_assertion",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'missing_failure_assertion': 'test_fails_without_assertion'}}\n"
            "\n"
            "def test_fails_without_assertion():\n"
            "    SchemaValidator().validate({'todo': {}, 'runtime': {}})\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "negative_test_missing_failure_assertion")

    def test_fails_when_negative_test_asserts_failure_without_validator_invocation(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("missing_validator_invocation",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'missing_validator_invocation': 'test_fails_without_invocation'}}\n"
            "\n"
            "def test_fails_without_invocation():\n"
            "    result = type('Result', (), {'status': 'fail'})()\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "negative_test_missing_validator_invocation")

    def test_fails_when_token_exists_only_outside_negative_test(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("token_outside_negative",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'token_outside_negative': 'test_fails_without_local_token'}}\n"
            "\n"
            "def test_fails_without_local_token():\n"
            "    result = validator.validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "coverage_token_outside_negative_test")

    def test_passes_when_negative_test_invokes_validator_and_asserts_failure(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("valid_direct_negative",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'valid_direct_negative': 'test_fails_with_validator_invocation_and_assertion'}}\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "pass")

    def test_passes_when_negative_test_uses_approved_validator_helper(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("valid_helper_negative",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'valid_helper_negative': 'test_fails_with_validator_helper'}}\n"
            "\n"
            "def validate_schema(source):\n"
            "    return SchemaValidator().validate(source)\n"
            "\n"
            "def test_fails_with_validator_helper():\n"
            "    result = validate_schema({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "pass")

    def test_fails_when_coverage_mapping_references_missing_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "test_unknown.py"
            original_registered = validator_coverage.registered_validator_names
            original_contracts = validator_coverage.validator_coverage_contracts
            validator_coverage.registered_validator_names = lambda: ("unknown_validator",)
            validator_coverage.validator_coverage_contracts = lambda: (
                ValidatorTestContract("unknown_validator", missing_path, "UnknownValidator", ("missing_file",)),
            )
            try:
                result = ValidatorCoverageValidator().validate({})
            finally:
                validator_coverage.registered_validator_names = original_registered
                validator_coverage.validator_coverage_contracts = original_contracts

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_test_file")
        self.assertEqual(result.meta["validator_name"], "unknown_validator")

    def test_fails_when_required_marker_metadata_is_missing(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_coverage_metadata")

    def test_fails_when_required_marker_is_missing(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker", "missing_marker"),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_with_validator_invocation_and_assertion'}}\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "missing_required_marker")
        self.assertEqual(result.meta["marker_name"], "missing_marker")

    def test_fails_when_metadata_contains_unknown_marker(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_with_validator_invocation_and_assertion', 'unknown_marker': 'test_fails_with_validator_invocation_and_assertion'}}\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "unknown_marker")
        self.assertEqual(result.meta["marker_name"], "unknown_marker")

    def test_fails_when_marker_maps_to_missing_test_function(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_not_present'}}\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "mapped_test_function_missing")
        self.assertEqual(result.meta["marker_name"], "required_marker")

    def test_fails_when_marker_maps_to_placeholder_test(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_placeholder'}}\n"
            "\n"
            "def test_fails_placeholder():\n"
            "    pass\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "mapped_test_not_behavioral_negative")
        self.assertEqual(result.meta["marker_name"], "required_marker")

    def test_fails_when_marker_maps_to_test_without_failure_assertion(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_without_assertion'}}\n"
            "\n"
            "def test_fails_without_assertion():\n"
            "    SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "mapped_test_not_behavioral_negative")

    def test_fails_when_marker_maps_to_test_without_validator_invocation(self):
        result = self.validate_single_contract(
            "schema",
            "SchemaValidator",
            ("required_marker",),
            "from harness.validators_impl.schema import SchemaValidator\n"
            "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_without_invocation'}}\n"
            "\n"
            "def test_fails_without_invocation():\n"
            "    result = type('Result', (), {'status': 'fail'})()\n"
            "    assert result.status == 'fail'\n"
            "\n"
            "def test_fails_with_validator_invocation_and_assertion():\n"
            "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
            "    assert result.status == 'fail'\n",
        )

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.meta["reason"], "mapped_test_not_behavioral_negative")

    def test_failure_diagnostics_name_validator_marker_and_requirement(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_path = Path(temporary_directory) / "test_schema.py"
            test_path.write_text(
                "from harness.validators_impl.schema import SchemaValidator\n"
                "KOZO_NEGATIVE_COVERAGE = {'schema': {'required_marker': 'test_fails_not_present'}}\n"
                "def test_fails_with_validator_invocation_and_assertion():\n"
                "    result = SchemaValidator().validate({'todo': {}, 'runtime': {}})\n"
                "    assert result.status == 'fail'\n"
            )
            original_registered = validator_coverage.registered_validator_names
            original_contracts = validator_coverage.validator_coverage_contracts
            validator_coverage.registered_validator_names = lambda: ("schema",)
            validator_coverage.validator_coverage_contracts = lambda: (
                ValidatorTestContract("schema", test_path, "SchemaValidator", ("required_marker",)),
            )
            try:
                result = ValidatorCoverageValidator().validate({})
            finally:
                validator_coverage.registered_validator_names = original_registered
                validator_coverage.validator_coverage_contracts = original_contracts

        self.assertEqual(result.status, "fail")
        self.assertIn("schema", result.detail)
        self.assertIn("mapped_test_function_missing", result.detail)
        self.assertIn("required_marker", result.detail)
        self.assertEqual(result.meta["marker_name"], "required_marker")

    def test_governance_validator_covers_itself(self):
        contract = validator_coverage._VALIDATOR_TEST_CONTRACTS["validator_coverage"]

        self.assertTrue(contract.test_path.is_file())
        self.assertTrue(validator_coverage.test_file_has_negative_case(contract.test_path))
        self.assertIn("ValidatorCoverageValidator", contract.test_path.read_text())

    def validate_single_contract(
        self,
        validator_name: str,
        coverage_token: str,
        required_markers: tuple[str, ...],
        source: str,
    ):
        with tempfile.TemporaryDirectory() as temporary_directory:
            test_path = Path(temporary_directory) / f"test_{validator_name}.py"
            test_path.write_text(source)
            original_registered = validator_coverage.registered_validator_names
            original_contracts = validator_coverage.validator_coverage_contracts
            validator_coverage.registered_validator_names = lambda: (validator_name,)
            validator_coverage.validator_coverage_contracts = lambda: (
                ValidatorTestContract(validator_name, test_path, coverage_token, required_markers),
            )
            try:
                return ValidatorCoverageValidator().validate({})
            finally:
                validator_coverage.registered_validator_names = original_registered
                validator_coverage.validator_coverage_contracts = original_contracts


if __name__ == "__main__":
    unittest.main()
