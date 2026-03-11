from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class OdinValidator(BaseValidator):
    name = "odin"
    subsystem = "odin"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Odin placeholder passed")
