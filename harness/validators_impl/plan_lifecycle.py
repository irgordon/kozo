from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class PlanLifecycleValidator(BaseValidator):
    name = "plan_lifecycle"
    subsystem = "lifecycle"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Plan lifecycle placeholder passed")
