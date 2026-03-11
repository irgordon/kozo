from harness.codes import OK, EXPLANATION_SUMMARY_REQUIRED
from harness.invariants import get_predicate
from harness.validator import BaseValidator, ValidationResult

_nonempty_string_list = get_predicate("nonempty_string_list")

class ExplanationValidator(BaseValidator):
    name = "explanation"
    subsystem = "explanation"

    def validate(self, bundle):
        todo = bundle.get("todo", {})
        steps = todo.get("steps", [])
        required = (
            todo.get("plan_status") == "complete"
            or any(
                step.get("status") == "done" and step.get("kind") in {"edit", "docs"}
                for step in steps
            )
        )
        valid = _nonempty_string_list(todo.get("explanation_summary"))
        if required and not valid:
            return ValidationResult.fail(
                code=EXPLANATION_SUMMARY_REQUIRED,
                detail="Explanation summary required but missing or invalid",
                action="Add a non-empty explanation_summary list describing completed edits",
            )
        return ValidationResult.pass_(code=OK, detail="Explanation summary is present when the plan requires it")
