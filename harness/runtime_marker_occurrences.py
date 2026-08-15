from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

RING3_ENTER_MARKER = "KOZO_RING3_ENTER"
RING0_RETURN_MARKER = "KOZO_RING0_RETURN_OK"
RUNTIME_RETURN_MARKER = "KOZO_RUNTIME_RETURN_OK"


def extract_marker_occurrences(text: str, catalog: Iterable[str]) -> list[str]:
    known_markers = frozenset(catalog)
    return [line.strip() for line in text.splitlines() if line.strip() in known_markers]


def marker_occurrence_counts(markers: Sequence[str]) -> dict[str, int]:
    return dict(sorted(Counter(markers).items()))


def exact_marker_line_count(text: str, marker: str) -> int:
    return sum(line.strip() == marker for line in text.splitlines())


def marker_occurs_as_governed(
    text: str,
    marker: str,
    expected: Sequence[str],
) -> bool:
    return exact_marker_line_count(text, marker) == expected.count(marker)


def completed_session_count(markers: Sequence[str]) -> int:
    return markers.count(RING0_RETURN_MARKER)


def active_or_failed_session_ordinal(markers: Sequence[str]) -> int:
    entered = markers.count(RING3_ENTER_MARKER)
    completed = completed_session_count(markers)
    if entered > 2:
        return 3
    if completed >= 2:
        return 0
    return completed + 1


def repeated_session_blocker(markers: Sequence[str], expected: Sequence[str]) -> str:
    entered = markers.count(RING3_ENTER_MARKER)
    completed = completed_session_count(markers)
    if entered > 2:
        return "unexpected_third_session"
    if tuple(markers) == tuple(expected):
        return "none"
    if tuple(markers) != tuple(expected[: len(markers)]):
        return "qemu_timeout"
    if entered == 0:
        return "first_session_not_entered"
    if completed == 0:
        return "first_session_not_completed"
    if entered == 1:
        return "between_session_reset_failed"
    if completed == 1:
        return "second_session_not_completed"
    return _later_runtime_blocker(len(markers))


def _later_runtime_blocker(observed_count: int) -> str:
    blockers = {
        45: "later_runtime_continuation_not_reached",
        46: "runtime_status_query_not_completed",
        47: "first_governed_capability_not_proven",
        48: "runtime_state_update_not_reached",
        49: "runtime_state_update_not_completed",
        50: "second_governed_capability_not_proven",
        51: "runtime_return_not_reached",
    }
    return blockers.get(observed_count, "qemu_timeout")


def marker_sequence_is_complete(markers: Sequence[str], expected: Sequence[str]) -> bool:
    return tuple(markers) == tuple(expected)
