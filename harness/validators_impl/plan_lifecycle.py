from harness.codes import OK, PLAN_STATUS_INVALID, STEP_ORDER_INVALID
from harness.registry import PLAN_STATUSES, STEP_STATUSES
from harness.validator import BaseValidator, ValidationResult


def _step_ids(steps):
    return [step.get("id") for step in steps]


class PlanLifecycleValidator(BaseValidator):
    name = "plan_lifecycle"
    subsystem = "lifecycle"

    def validate(self, artifact_bundle):
        todo = artifact_bundle["todo"]
        runtime = artifact_bundle["runtime"]
        steps = todo["steps"]
        step_ids = _step_ids(steps)
        if step_ids != sorted(step_ids) or len(step_ids) != len(set(step_ids)):
            return ValidationResult.fail(
                code=STEP_ORDER_INVALID,
                detail="Step identifiers must be unique and ordered ascending",
                action="Renumber tasks/todo.json steps in canonical order",
            )
        if todo["plan_status"] not in PLAN_STATUSES or runtime["plan_status"] not in PLAN_STATUSES:
            return ValidationResult.fail(
                code=PLAN_STATUS_INVALID,
                detail="Plan status is outside the canonical protocol",
                action="Use a plan_status declared in harness/registry.py",
            )
        if runtime["plan_status"] != todo["plan_status"]:
            return ValidationResult.fail(
                code=PLAN_STATUS_INVALID,
                detail="tasks/runtime.json and tasks/todo.json disagree on plan_status",
                action="Keep runtime and todo plan_status values aligned",
            )
        if runtime["current_step_id"] not in set(step_ids):
            return ValidationResult.fail(
                code=PLAN_STATUS_INVALID,
                detail="runtime.current_step_id does not reference a declared step",
                action="Point current_step_id at a step in tasks/todo.json",
            )
        if any(step["status"] not in STEP_STATUSES for step in steps):
            return ValidationResult.fail(
                code=PLAN_STATUS_INVALID,
                detail="A step uses a non-canonical step status",
                action="Use step statuses declared in harness/registry.py",
            )
        if runtime["plan_status"] == "complete" and any(step["status"] != "done" for step in steps):
            return ValidationResult.fail(
                code=PLAN_STATUS_INVALID,
                detail="A complete plan must have every step marked done",
                action="Mark each completed step as done before closing the plan",
            )
        return ValidationResult.pass_(code=OK, detail="Plan lifecycle is internally consistent")
