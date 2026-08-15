from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness import bounded_repeated_user_session_contract as contract_module
from harness.codes import BOUNDED_REPEATED_USER_SESSION_CONTRACT_INVALID, OK
from harness.validators_impl import bounded_repeated_user_session_contract as validator_module


class BoundedRepeatedUserSessionContractTests(unittest.TestCase):
    def test_valid_contract_passes(self):
        self.assertEqual(self.validate_fixture().code, OK)

    def test_requires_exactly_two_sessions(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "authority", "required_session_count", 3)), "contract_schema_violation")

    def test_rejects_invalid_coordinator_size(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "coordinator", "size_bytes", 40)), "contract_schema_violation")

    def test_rejects_invalid_coordinator_alignment(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "coordinator", "alignment_bytes", 4)), "contract_schema_violation")

    def test_rejects_invalid_session_ordinal(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "session", "ordinals", [1, 3])), "invalid_session_contract")

    def test_rejects_completed_count_above_two(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "coordinator", "completed_session_count_maximum", 3)), "contract_schema_violation")

    def test_rejects_total_transition_count_above_four(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "coordinator", "observed_total_transition_count_maximum", 5)), "contract_schema_violation")

    def test_rejects_nonzero_reserved_terminal_field(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "coordinator", "terminal_state", "reserved", 1)), "contract_schema_violation")

    def test_rejects_coordinator_identity_field(self):
        def mutate(data):
            data["coordinator"]["fields"][-1]["name"] = "context_identity"
            return data
        self.assert_reason(self.validate_fixture(mutate), "invalid_coordinator")

    def test_rejects_unknown_root_field(self):
        def mutate(data):
            data["unknown"] = True
            return data
        self.assert_reason(self.validate_fixture(mutate), "contract_schema_violation")

    def test_session_identities_are_nonzero_and_distinct(self):
        contract = contract_module.load_bounded_repeated_user_session_contract()
        first, second = contract_module.session_identities(contract)
        self.assertNotEqual(first, 0)
        self.assertNotEqual(second, 0)
        self.assertNotEqual(first, second)

    def test_rejects_identity_reuse(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "identity", "session_2", "0x4b4f5a4f43545831")), "contract_schema_violation")

    def test_rejects_pointer_derived_identity(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "identity", "pointer_derived", True)), "contract_schema_violation")

    def test_rejects_user_selected_session_count(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "authority", "user_selectable_session_count", True)), "contract_schema_violation")

    def test_rejects_missing_result_reset_readback(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "reset_boundary", "readback_required", False)), "contract_schema_violation")

    def test_rejects_silent_reset_repair(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "reset_boundary", "silent_repair", True)), "contract_schema_violation")

    def test_rejects_third_session(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "session", "third_session", "accepted")), "contract_schema_violation")

    def test_rejects_fifth_transition(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "session", "fifth_transition", "accepted")), "contract_schema_violation")

    def test_rejects_changed_failure_code(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "failure_codes", "IDENTITY_REUSE", 18)), "contract_schema_violation")

    def test_requires_52_ordered_occurrences(self):
        self.assert_reason(self.validate_fixture(lambda data: self.set_value(data, "marker_policy", "final_occurrence_count", 41)), "contract_schema_violation")

    def validate_fixture(self, mutate=None):
        data = json.loads(contract_module.CONTRACT_PATH.read_text())
        if mutate is not None:
            data = mutate(copy.deepcopy(data))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contract.json"
            path.write_text(json.dumps(data))
            original = validator_module.contract_module.CONTRACT_PATH
            validator_module.contract_module.CONTRACT_PATH = path
            try:
                return validator_module.BoundedRepeatedUserSessionContractValidator().validate({})
            finally:
                validator_module.contract_module.CONTRACT_PATH = original

    def assert_reason(self, result, reason):
        self.assertEqual(result.code, BOUNDED_REPEATED_USER_SESSION_CONTRACT_INVALID)
        self.assertIn(reason, result.detail)

    @staticmethod
    def set_value(data, *path_and_value):
        *path, value = path_and_value
        target = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        return data


if __name__ == "__main__":
    unittest.main()
