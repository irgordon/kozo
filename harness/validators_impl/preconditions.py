from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class PreconditionsValidator(BaseValidator):
    name = "preconditions"
    subsystem = "preconditions"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Preconditions placeholder passed")
