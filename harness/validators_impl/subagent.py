from harness.codes import OK, SUBAGENT_SCOPE_VIOLATION
from harness.validator import BaseValidator, ValidationResult


class SubagentValidator(BaseValidator):
    name = "subagent"
    subsystem = "subagent"

    def validate(self, artifact_bundle):
        subagent_data = artifact_bundle["todo"].get("subagents") or artifact_bundle["runtime"].get("subagents")
        if subagent_data:
            return ValidationResult.fail(
                code=SUBAGENT_SCOPE_VIOLATION,
                detail="Subagent scope is not part of this minimal bootstrap protocol",
                action="Remove subagent declarations until the harness defines that protocol",
            )
        return ValidationResult.pass_(code=OK, detail="No subagent scope needs validation in this bootstrap plan")
