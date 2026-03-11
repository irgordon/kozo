from __future__ import annotations

import re
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Callable, Dict

from harness.registry import VERIFICATION_SECTIONS

Predicate = Callable[[Any], bool]

NONEMPTY_STRING_PATTERN = r".*\S.*"
UTC_TIMESTAMP_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
_VERIFICATION_SECTION_PATTERN = "|".join(VERIFICATION_SECTIONS)
VERIFICATION_REF_PATTERN = (
    r"^verification\."
    rf"({_VERIFICATION_SECTION_PATTERN})"
    r"\[[0-9]+\]$"
)

_NONEMPTY_STRING_RE = re.compile(NONEMPTY_STRING_PATTERN)
_UTC_TIMESTAMP_RE = re.compile(UTC_TIMESTAMP_PATTERN)
_VERIFICATION_REF_RE = re.compile(VERIFICATION_REF_PATTERN)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(_NONEMPTY_STRING_RE.fullmatch(value))


def _is_string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_nonempty_string(item) for item in value)


def _is_nonempty_string_list(value: Any) -> bool:
    return _is_string_list(value) and len(value) > 0


def _is_utc_timestamp(value: Any) -> bool:
    return isinstance(value, str) and bool(_UTC_TIMESTAMP_RE.fullmatch(value))


def _is_verification_ref(value: Any) -> bool:
    return isinstance(value, str) and bool(_VERIFICATION_REF_RE.fullmatch(value))


_INVARIANTS: Dict[str, Dict[str, Any]] = {
    "nonempty_string": {
        "predicate": _is_nonempty_string,
        "schema": {
            "type": "string",
            "pattern": NONEMPTY_STRING_PATTERN,
        },
    },
    "string_list": {
        "predicate": _is_string_list,
        "schema": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": NONEMPTY_STRING_PATTERN,
            },
        },
    },
    "nonempty_string_list": {
        "predicate": _is_nonempty_string_list,
        "schema": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "string",
                "pattern": NONEMPTY_STRING_PATTERN,
            },
        },
    },
    "utc_timestamp": {
        "predicate": _is_utc_timestamp,
        "schema": {
            "type": "string",
            "pattern": UTC_TIMESTAMP_PATTERN,
        },
    },
    "verification_ref": {
        "predicate": _is_verification_ref,
        "schema": {
            "type": "string",
            "pattern": VERIFICATION_REF_PATTERN,
        },
    },
}

INVARIANTS = MappingProxyType(_INVARIANTS)


def get_predicate(name: str) -> Predicate:
    invariant = INVARIANTS.get(name)
    if invariant is None:
        raise ValueError(f"Unknown invariant: {name}")
    return invariant["predicate"]


def get_schema(name: str) -> Dict[str, Any]:
    invariant = INVARIANTS.get(name)
    if invariant is None:
        raise ValueError(f"Unknown invariant: {name}")
    return deepcopy(invariant["schema"])
