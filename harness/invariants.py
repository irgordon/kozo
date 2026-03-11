from __future__ import annotations
import re
from copy import deepcopy
from types import MappingProxyType
from typing import Any, Callable, Dict

Predicate = Callable[[Any], bool]

_VERIFICATION_REF_PATTERN = (
    r"^verification\."
    r"(tests_run|logs|diffs|invariants|expected_behavior|actual_behavior)"
    r"\[[0-9]+\]$"
)

_VERIFICATION_REF_RE = re.compile(_VERIFICATION_REF_PATTERN)

def _nonempty_string_list_pred(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0 and all(
        isinstance(x, str) and x.strip() for x in value
    )

def _string_list_pred(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(x, str) and x.strip() for x in value
    )

def _verification_ref_pred(value: Any) -> bool:
    return isinstance(value, str) and bool(_VERIFICATION_REF_RE.fullmatch(value))

_INVARIANTS: Dict[str, Dict[str, Any]] = {
    "nonempty_string_list": {
        "predicate": _nonempty_string_list_pred,
        "schema": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "string", "pattern": r".*\S.*"},
        },
    },
    "string_list": {
        "predicate": _string_list_pred,
        "schema": {
            "type": "array",
            "items": {"type": "string", "pattern": r".*\S.*"},
        },
    },
    "verification_ref": {
        "predicate": _verification_ref_pred,
        "schema": {
            "type": "string",
            "pattern": _VERIFICATION_REF_PATTERN,
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