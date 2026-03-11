from __future__ import annotations

from typing import Any, Dict

from harness.registry import ARTIFACT_VERSION
from harness.validators_impl.schema import validate_named_document


def _find_current_step(todo: Dict[str, Any], step_id: int) -> Dict[str, Any]:
    for step in todo.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise ValueError(f"Current step {step_id} was not found in tasks/todo.json")


def _derive_mode(runtime: Dict[str, Any]) -> str:
    if runtime.get("plan_status") == "complete":
        return "complete"
    if runtime.get("halted"):
        return "halted"
    if runtime.get("replan_required"):
        return "replan"
    return "execute"


def _build_constraints(runtime: Dict[str, Any]) -> list[str]:
    if runtime.get("plan_status") == "complete":
        return [
            "Plan is complete; any further edits require a new planned step.",
            "Fail closed if a file falls outside the declared task scope.",
        ]
    return [
        "Only edit files declared in current_step.files_expected.",
        "Fail closed if the next verification reports any failed check.",
    ]


def summarize(todo: Dict[str, Any], runtime: Dict[str, Any], verify: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_current_step(todo, runtime["current_step_id"])
    context = {
        "artifact_version": ARTIFACT_VERSION,
        "task_id": runtime["task_id"],
        "task_title": runtime["task_title"],
        "mode": _derive_mode(runtime),
        "current_step": {
            "id": step["id"],
            "kind": step["kind"],
            "title": step["title"],
            "files_expected": step["files_expected"],
            "verification_refs": step["verification_refs"],
        },
        "constraints": _build_constraints(runtime),
        "active_rules": [],
        "recent_failures": verify["failed_checks"],
        "next_verification": step["verification_refs"],
        "halt_conditions": [
            "Any file outside the declared task scope changes.",
            "The current step failure count reaches 2.",
            "Verification returns status=fail after an execution attempt.",
        ],
        "updated_at": runtime["updated_at"],
    }
    validate_named_document("agent_context", context)
    return context
