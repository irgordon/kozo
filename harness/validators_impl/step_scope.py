from harness.codes import (
    OK,
    STEP_SCOPE_EMPTY_DONE_STEP,
    STEP_SCOPE_OUTSIDE_TASK_SCOPE,
    STEP_SCOPE_UNPLANNED_FILE,
)
from harness.validator import BaseValidator, ValidationResult


def _matches_scope(path, scope):
    if scope.endswith("/"):
        return path.startswith(scope)
    return path == scope or path.startswith(f"{scope}/")


def _allowed_files(todo, runtime):
    steps = todo["steps"]
    if runtime["plan_status"] == "complete":
        return {path for step in steps for path in step["files_expected"]}
    for step in steps:
        if step["id"] == runtime["current_step_id"]:
            return set(step["files_expected"])
    return set()


class StepScopeValidator(BaseValidator):
    name = "step_scope"
    subsystem = "step_scope"

    def validate(self, artifact_bundle):
        todo = artifact_bundle["todo"]
        runtime = artifact_bundle["runtime"]
        changed_files = artifact_bundle["changed_files"]
        for step in todo["steps"]:
            if step["status"] == "done" and not step["files_expected"]:
                return ValidationResult.fail(
                    code=STEP_SCOPE_EMPTY_DONE_STEP,
                    detail=f"Done step {step['id']} must declare at least one expected file",
                    action="Populate files_expected for every completed step",
                )
        task_scope = todo["file_scope"]
        for path in changed_files:
            if not any(_matches_scope(path, scope) for scope in task_scope):
                return ValidationResult.fail(
                    code=STEP_SCOPE_OUTSIDE_TASK_SCOPE,
                    detail=f"Changed file {path} falls outside todo.file_scope",
                    action="Restrict edits to files declared in tasks/todo.json",
                )
        allowed = _allowed_files(todo, runtime)
        for path in changed_files:
            if path not in allowed:
                return ValidationResult.fail(
                    code=STEP_SCOPE_UNPLANNED_FILE,
                    detail=f"Changed file {path} is not declared in the active plan scope",
                    action="Add the file to a planned step or revert the out-of-scope edit",
                )
        return ValidationResult.pass_(code=OK, detail="Changed files stay within the declared step scope")
