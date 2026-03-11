from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class SubagentValidator(BaseValidator):
    name = "subagent"
    subsystem = "subagent"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Subagent placeholder passed")
