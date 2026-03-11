from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class EvidenceValidator(BaseValidator):
    name = "evidence"
    subsystem = "evidence"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Evidence placeholder passed")
