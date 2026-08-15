from __future__ import annotations

import unittest

from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.runtime_marker_occurrences import (
    active_or_failed_session_ordinal,
    completed_session_count,
    extract_marker_occurrences,
    marker_occurrence_counts,
    marker_sequence_is_complete,
    repeated_session_blocker,
)


class RuntimeMarkerOccurrenceTests(unittest.TestCase):
    def setUp(self):
        self.expected = get_smoke_marker_order()

    def test_exact_52_marker_sequence_is_complete(self):
        self.assertEqual(len(self.expected), 52)
        self.assertTrue(marker_sequence_is_complete(self.expected, self.expected))

    def test_duplicate_transaction_blocks_are_preserved(self):
        text = "\n".join(self.expected) + "\n"
        observed = extract_marker_occurrences(text, set(self.expected))
        self.assertEqual(observed, list(self.expected))
        self.assertEqual(observed.count("KOZO_RING3_ENTER"), 2)
        self.assertEqual(observed.count("KOZO_RING0_RETURN_OK"), 2)

    def test_deduplicated_sequence_is_rejected(self):
        observed = list(dict.fromkeys(self.expected))
        self.assertFalse(marker_sequence_is_complete(observed, self.expected))

    def test_missing_first_block_marker_is_rejected(self):
        observed = list(self.expected)
        del observed[24]
        self.assertFalse(marker_sequence_is_complete(observed, self.expected))

    def test_missing_second_block_marker_is_rejected(self):
        observed = list(self.expected)
        del observed[35]
        self.assertFalse(marker_sequence_is_complete(observed, self.expected))

    def test_interleaved_blocks_are_rejected(self):
        observed = list(self.expected)
        observed[34], observed[35] = observed[35], observed[34]
        self.assertFalse(marker_sequence_is_complete(observed, self.expected))

    def test_suffix_before_second_block_is_rejected(self):
        observed = list(self.expected[:34]) + list(self.expected[45:]) + list(self.expected[34:45])
        self.assertFalse(marker_sequence_is_complete(observed, self.expected))

    def test_third_block_is_rejected(self):
        observed = list(self.expected[:45]) + list(self.expected[23:34]) + list(self.expected[45:])
        self.assertEqual(repeated_session_blocker(observed, self.expected), "unexpected_third_session")

    def test_first_session_not_entered_is_classified(self):
        self.assertEqual(repeated_session_blocker(self.expected[:23], self.expected), "first_session_not_entered")

    def test_first_session_not_completed_is_classified(self):
        self.assertEqual(repeated_session_blocker(self.expected[:28], self.expected), "first_session_not_completed")

    def test_between_session_reset_failure_is_classified(self):
        self.assertEqual(repeated_session_blocker(self.expected[:34], self.expected), "between_session_reset_failed")

    def test_second_session_not_completed_is_classified(self):
        self.assertEqual(repeated_session_blocker(self.expected[:40], self.expected), "second_session_not_completed")

    def test_later_runtime_continuation_failure_is_classified(self):
        self.assertEqual(repeated_session_blocker(self.expected[:45], self.expected), "later_runtime_continuation_not_reached")

    def test_occurrence_metadata_reports_two_completed_sessions(self):
        counts = marker_occurrence_counts(self.expected)
        self.assertEqual(counts["KOZO_RING3_ENTER"], 2)
        self.assertEqual(counts["KOZO_RING0_RETURN_OK"], 2)
        self.assertEqual(completed_session_count(self.expected), 2)
        self.assertEqual(active_or_failed_session_ordinal(self.expected), 0)

    def test_runtime_return_remains_last(self):
        self.assertEqual(self.expected[-1], "KOZO_RUNTIME_RETURN_OK")


if __name__ == "__main__":
    unittest.main()
