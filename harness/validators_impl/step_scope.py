from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class StepScopeValidator(BaseValidator):
    name = "step_scope"
    subsystem = "step_scope"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Step scope placeholder passed")
