from __future__ import annotations

import re
from typing import Any, Dict, List

from harness.codes import REPLAN_REQUIRED, STEP_FAILURE_THRESHOLD
from harness.invariants import VERIFICATION_REF_PATTERN
from harness.registry import ARTIFACT_VERSION
from harness.validators_impl.schema import validate_named_document

_verification_ref_re = re.compile(VERIFICATION_REF_PATTERN)


def _find_current_step(todo: Dict[str, Any], step_id: int) -> Dict[str, Any]:
    for step in todo.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise ValueError(f"Current step {step_id} was not found in tasks/todo.json")


def _resolve_verification_ref(todo: Dict[str, Any], ref: str) -> Dict[str, Any]:
    match = _verification_ref_re.fullmatch(ref)
    if match is None:
        raise ValueError(f"Invalid verification ref: {ref}")
    prefix, index_text = ref.split("[", 1)
    section_name = prefix.split(".", 1)[1]
    section = todo["verification"][section_name]
    index = int(index_text[:-1])
    if index >= len(section):
        raise ValueError(f"Verification ref out of range: {ref}")
    return {"section": section_name, "index": index, "value": section[index]}


def _build_next_verification(step: Dict[str, Any], todo: Dict[str, Any]) -> List[str]:
    next_refs: List[str] = []
    seen_refs = set()
    for ref in step["verification_refs"]:
        _resolve_verification_ref(todo, ref)
        if ref not in seen_refs:
            seen_refs.add(ref)
            next_refs.append(ref)
    return next_refs


def _extract_next_commands(next_refs: List[str], todo: Dict[str, Any]) -> List[str]:
    commands: List[str] = []
    seen_commands = set()
    for ref in next_refs:
        resolved = _resolve_verification_ref(todo, ref)
        if resolved["section"] != "tests_run":
            continue
        command = resolved["value"]["command"]
        if command not in seen_commands:
            seen_commands.add(command)
            commands.append(command)
    return commands


def _is_recovery_state(runtime: Dict[str, Any], verify: Dict[str, Any]) -> bool:
    return bool(verify.get("failed_checks")) and not runtime.get("replan_required") and not runtime.get("halted")


def _build_mode(runtime: Dict[str, Any], verify: Dict[str, Any]) -> str:
    if runtime.get("halted"):
        return "halted"
    if runtime.get("replan_required") or verify.get("summary_code") == REPLAN_REQUIRED:
        return "replan"
    if _is_recovery_state(runtime, verify):
        return "halted"
    if runtime.get("plan_status") == "complete":
        return "complete"
    return "execute"


def _build_constraints(runtime: Dict[str, Any], verify: Dict[str, Any]) -> List[str]:
    if runtime.get("plan_status") == "complete":
        return [
            "Plan is complete; any further edits require a new planned step.",
            "Fail closed if a file falls outside the declared task scope.",
        ]
    if _is_recovery_state(runtime, verify):
        return [
            "Recovery is required before continuing execution.",
            "Fail closed until the failed verification checks are addressed and verify passes.",
        ]
    return [
        "Only edit files declared in current_step.files_expected.",
        "Fail closed if the next verification reports any failed check.",
    ]


def _build_active_rules(runtime: Dict[str, Any], verify: Dict[str, Any], next_commands: List[str]) -> List[str]:
    rules: List[str] = [f"Run: {command}" for command in next_commands]
    if verify.get("summary_code") == STEP_FAILURE_THRESHOLD:
        rules.append("Failure threshold reached; halt and recover before more edits.")
    if verify.get("summary_code") == REPLAN_REQUIRED or runtime.get("replan_required"):
        rules.append("Replan before continuing work.")
    if _is_recovery_state(runtime, verify):
        rules.append("Recovery required: fix the failed checks before execution resumes.")
    return rules


def summarize(todo: Dict[str, Any], runtime: Dict[str, Any], verify: Dict[str, Any]) -> Dict[str, Any]:
    step = _find_current_step(todo, runtime["current_step_id"])
    next_verification = _build_next_verification(step, todo)
    next_commands = _extract_next_commands(next_verification, todo)
    context = {
        "artifact_version": ARTIFACT_VERSION,
        "task_id": runtime["task_id"],
        "task_title": runtime["task_title"],
        "mode": _build_mode(runtime, verify),
        "current_step": {
            "id": step["id"],
            "kind": step["kind"],
            "title": step["title"],
            "files_expected": step["files_expected"],
            "verification_refs": step["verification_refs"],
        },
        "constraints": _build_constraints(runtime, verify),
        "active_rules": _build_active_rules(runtime, verify, next_commands),
        "recent_failures": verify["failed_checks"],
        "next_verification": next_verification,
        "halt_conditions": [
            "Any file outside the declared task scope changes.",
            "The current step failure count reaches 2.",
            "Verification returns status=fail after an execution attempt.",
        ],
        "updated_at": runtime["updated_at"],
    }
    validate_named_document("agent_context", context)
    return context
