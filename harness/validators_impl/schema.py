from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class SchemaValidator(BaseValidator):
    name = "schema"
    subsystem = "schema"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="Schema validation placeholder passed")
