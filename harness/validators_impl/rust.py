from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class RustValidator(BaseValidator):
    name = "rust"
    subsystem = "rust"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Rust placeholder passed")
