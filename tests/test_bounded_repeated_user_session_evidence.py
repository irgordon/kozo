from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from harness.codes import BOUNDED_REPEATED_USER_SESSION_EVIDENCE_INVALID, OK
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.runtime_marker_occurrences import marker_occurrence_counts
from harness.validators_impl import bounded_repeated_user_session_evidence as validator_module
from harness.validators_impl.bounded_repeated_user_session_evidence import (
    BoundedRepeatedUserSessionEvidenceValidator,
)


class BoundedRepeatedUserSessionEvidenceTests(unittest.TestCase):
    def test_valid_evidence_passes(self):
        result = self.validate_fixture()
        self.assertEqual((result.status, result.code), ("pass", OK))

    def test_requires_coordinator_size_assertion(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("#assert(size_of(Repeated_User_Session_Coordinator) == REPEATED_SESSION_COORDINATOR_SIZE)\n", "")), "coordinator_invalid")

    def test_requires_linker_alignment(self):
        self.assert_reason(self.validate_fixture(linker=lambda text: text.replace("(repeated_user_session_coordinator % 8) == 0", "removed")), "coordinator_linker_invalid")

    def test_requires_first_session(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("execute_first_bounded_user_session()", "removed", 1)), "session_flow_invalid")

    def test_requires_second_session(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("execute_second_bounded_user_session()", "removed", 1)), "session_flow_invalid")

    def test_rejects_third_session_call(self):
        def mutation(text):
            needle = "\treturn finalize_repeated_session_coordinator()"
            return text.replace(needle, "\texecute_fixed_user_session(SECOND_SESSION_ORDINAL)\n" + needle, 1)
        self.assert_reason(self.validate_fixture(runtime=mutation), "session_count_unbounded")

    def test_rejects_session_loop(self):
        mutation = lambda text: text.replace("\tinitialize_repeated_session_coordinator()", "\twhile false {}\n\tinitialize_repeated_session_coordinator()", 1)
        self.assert_reason(self.validate_fixture(runtime=mutation), "session_count_unbounded")

    def test_requires_transaction_execution(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("execute_fixed_user_runtime_status_transaction()", "removed", 1)), "session_lifecycle_invalid")

    def test_requires_context_result_validation(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("validate_fixed_user_context_success_result()", "removed", 1)), "session_lifecycle_invalid")

    def test_requires_between_session_cleanup(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("validate_fixed_user_session_cleanup()", "removed", 1)), "reset_order_invalid")

    def test_requires_between_session_result_reset(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("reset_fixed_user_context_result()", "removed", 1)), "reset_order_invalid")

    def test_requires_context_reinitialization(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("reset_fixed_user_execution_context_for_reuse()", "removed", 1)), "reset_order_invalid")

    def test_requires_reset_readback(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("validate_fixed_user_session_reset_state()", "removed", 1)), "reset_order_invalid")

    def test_requires_terminal_result_reset(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("if reset_completed_fixed_user_session(", "if removed(", 1)), "reset_order_invalid")

    def test_requires_storage_zero_readback(self):
        mutation = lambda text: remove_from_range(
            text,
            "validate_fixed_user_session_reset_state:",
            "invalidate_fixed_user_session_state:",
            "    call fixed_user_session_storage_is_zero\n",
        )
        self.assert_reason(self.validate_fixture(privilege=mutation), "reset_readback_invalid")

    def test_requires_second_identity(self):
        self.assert_reason(self.validate_fixture(layout=lambda text: text.replace("%define FIXED_USER_CONTEXT_SECOND_OPAQUE_IDENTITY 0x4b4f5a4f43545832", "%define FIXED_USER_CONTEXT_SECOND_OPAQUE_IDENTITY 0x4b4f5a4f43545831")), "identity_sequence_invalid")

    def test_requires_two_pointer_policy_checks(self):
        self.assert_reason(self.validate_fixture(privilege=lambda text: text.replace("    call fixed_user_identity_is_non_pointer\n", "", 1)), "identity_pointer_policy_invalid")

    def test_requires_failure_invalidation(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("\tinvalidate_fixed_user_session_state()\n", "", 1)), "failure_cleanup_invalid")

    def test_requires_distinct_stale_result_failure(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("REPEATED_SESSION_FAILURE_STALE_CONTEXT_RESULT_BEFORE_SESSION", "removed")), "failure_codes_missing")

    def test_requires_unexpected_third_session_failure(self):
        self.assert_reason(self.validate_fixture(runtime=lambda text: text.replace("REPEATED_SESSION_FAILURE_UNEXPECTED_THIRD_SESSION", "removed")), "failure_codes_missing")

    def test_requires_elf_coordinator_geometry(self):
        self.assert_reason(self.validate_fixture(report=lambda value: set_report(value, "coordinator", "size_bytes", 40)), "elf_coordinator_invalid")

    def test_requires_zero_coordinator_overlap(self):
        self.assert_reason(self.validate_fixture(report=lambda value: set_record(value, "coordinator_overlap_count", 1)), "elf_coordinator_invalid")

    def test_requires_two_elf_session_calls(self):
        self.assert_reason(self.validate_fixture(report=lambda value: set_record(value, "session_call_count", 1)), "elf_flow_invalid")

    def test_rejects_hidden_third_elf_call(self):
        self.assert_reason(self.validate_fixture(report=lambda value: set_record(value, "total_session_call_count", 3)), "elf_flow_invalid")

    def test_requires_later_capability_gate(self):
        self.assert_reason(self.validate_fixture(report=lambda value: set_record(value, "later_capability_gate_valid", False)), "elf_flow_invalid")

    def test_requires_exact_52_occurrences(self):
        self.assert_reason(self.validate_fixture(metadata=lambda value: value | {"observed_markers": value["observed_markers"][:-1]}), "marker_sequence_invalid")

    def test_rejects_deduplicated_occurrences(self):
        self.assert_reason(self.validate_fixture(metadata=lambda value: value | {"observed_markers": list(dict.fromkeys(value["observed_markers"]))}), "marker_sequence_invalid")

    def test_requires_completed_session_count(self):
        self.assert_reason(self.validate_fixture(metadata=lambda value: value | {"completed_session_count": 1}), "runtime_count_invalid")

    def test_requires_terminal_active_ordinal(self):
        self.assert_reason(self.validate_fixture(metadata=lambda value: value | {"active_or_failed_session_ordinal": 2}), "runtime_count_invalid")

    def test_requires_occurrence_count_map(self):
        self.assert_reason(self.validate_fixture(metadata=lambda value: value | {"marker_occurrence_counts": {}}), "runtime_count_invalid")

    def test_rejects_third_serial_block(self):
        block = get_smoke_marker_order()[23:34]
        self.assert_reason(self.validate_fixture(serial=lambda text: text + "\n".join(block) + "\n"), "serial_sequence_invalid")

    def test_requires_serial_second_session(self):
        marker = "KOZO_RING0_RETURN_OK"
        self.assert_reason(self.validate_fixture(serial=lambda text: remove_last_line(text, marker)), "serial_sequence_invalid")

    def validate_fixture(self, **mutations):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.write_fixtures(root, mutations)
            originals = self.patch_paths(paths)
            try:
                return BoundedRepeatedUserSessionEvidenceValidator().validate({})
            finally:
                self.restore_paths(originals)

    def write_fixtures(self, root, mutations):
        paths = {}
        for name, source in source_paths().items():
            target = root / name
            value = source.read_text()
            mutation = mutations.get(name)
            target.write_text(mutation(value) if mutation else value)
            paths[name] = target
        paths["report"] = write_json(root / "report", validator_module._ELF_REPORT_PATH, mutations.get("report"))
        metadata = current_metadata()
        mutation = mutations.get("metadata")
        paths["metadata"] = root / "metadata"
        paths["metadata"].write_text(json.dumps(mutation(copy.deepcopy(metadata)) if mutation else metadata))
        serial = "\n".join(get_smoke_marker_order()) + "\n"
        mutation = mutations.get("serial")
        paths["serial"] = root / "serial"
        paths["serial"].write_text(mutation(serial) if mutation else serial)
        return paths

    def patch_paths(self, paths):
        mapping = {
            "_CONTRACT_PATH": paths["contract"],
            "_RUNTIME_PATH": paths["runtime"],
            "_PRIVILEGE_PATH": paths["privilege"],
            "_LAYOUT_PATH": paths["layout"],
            "_LINKER_PATH": paths["linker"],
            "_ELF_REPORT_PATH": paths["report"],
            "_METADATA_PATH": paths["metadata"],
            "_SERIAL_PATH": paths["serial"],
        }
        originals = {name: getattr(validator_module, name) for name in mapping}
        for name, path in mapping.items():
            setattr(validator_module, name, path)
        return originals

    def restore_paths(self, originals):
        for name, path in originals.items():
            setattr(validator_module, name, path)

    def assert_reason(self, result, reason):
        self.assertEqual((result.status, result.code), ("fail", BOUNDED_REPEATED_USER_SESSION_EVIDENCE_INVALID))
        self.assertEqual(result.meta["reason"], reason)
        self.assertIn("contract_field", result.meta)


def source_paths():
    return {
        "contract": validator_module._CONTRACT_PATH,
        "runtime": validator_module._RUNTIME_PATH,
        "privilege": validator_module._PRIVILEGE_PATH,
        "layout": validator_module._LAYOUT_PATH,
        "linker": validator_module._LINKER_PATH,
    }


def current_metadata():
    value = json.loads(validator_module._METADATA_PATH.read_text())
    markers = list(get_smoke_marker_order())
    value.update({
        "outcome": "pass",
        "blocker_category": "none",
        "observed_markers": markers,
        "expected_marker_count": 52,
        "observed_marker_count": 52,
        "marker_occurrence_counts": marker_occurrence_counts(markers),
        "completed_session_count": 2,
        "active_or_failed_session_ordinal": 0,
    })
    return value


def write_json(target, source, mutation):
    value = json.loads(source.read_text())
    target.write_text(json.dumps(mutation(copy.deepcopy(value)) if mutation else value))
    return target


def set_record(report, field, value):
    report["bounded_repeated_user_session"][field] = value
    return report


def set_report(report, section, field, value):
    report["bounded_repeated_user_session"][section][field] = value
    return report


def remove_from_range(text, start, end, token):
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    section = text[start_index:end_index].replace(token, "", 1)
    return text[:start_index] + section + text[end_index:]


def remove_last_line(text, marker):
    lines = text.splitlines()
    lines.pop(len(lines) - 1 - lines[::-1].index(marker))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    unittest.main()
