from __future__ import annotations
from typing import Dict, Any, List

def _find_current_step(todo: Dict[str, Any], step_id: int) -> Dict[str, Any]:
    for step in todo.get("steps", []):
        if step.get("id") == step_id:
            return step
    return {}

def summarize(todo: Dict[str, Any], runtime: Dict[str, Any], verify: Dict[str, Any]) -> Dict[str, Any]:

    step_id = runtime["current_step_id"]
    step = _find_current_step(todo, step_id)

    if not step:
        return {
            "artifact_version": "1",
            "status": "error",
            "code": "CURRENT_STEP_NOT_FOUND",
            "detail": f"Step {step_id} not found"
        }

    mode = "execute"
    if runtime.get("replan_required"):
        mode = "replan"
    if runtime.get("halted"):
        mode = "halted"
    if runtime.get("plan_status") == "complete":
        mode = "complete"

    return {
        "artifact_version": "1",
        "task_id": runtime["task_id"],
        "task_title": runtime["task_title"],
        "mode": mode,
        "current_step": {
            "id": step["id"],
            "kind": step["kind"],
            "title": step["title"],
            "files_expected": step.get("files_expected", []),
            "verification_refs": step.get("verification_refs", []),
        },
        "constraints": [
            "Do not edit files outside current_step.files_expected"
        ],
        "active_rules": [],
        "recent_failures": verify.get("failed_checks", []),
        "next_verification": [],
        "halt_conditions": [
            "Any file outside current_step.files_expected changes",
            "current step failure_count reaches 2",
            "verify status is fail after an execution attempt"
        ],
        "updated_at": runtime.get("updated_at"),
    }