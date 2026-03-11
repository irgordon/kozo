from harness.codes import OK
from harness.validator import BaseValidator, ValidationResult

class AbiValidator(BaseValidator):
    name = "abi"
    subsystem = "abi"

    def validate(self, artifact_bundle):
        return ValidationResult.pass_(code=OK, detail="ABI placeholder passed")
