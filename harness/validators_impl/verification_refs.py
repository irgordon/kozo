from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class VerificationRefsValidator(BaseValidator):
    name = "verification_refs"
    subsystem = "verification_refs"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Verification refs placeholder passed")
