from harness.codes import OK, PRECONDITION_UNCHECKED
from harness.validator import BaseValidator, ValidationResult


def _has_verification_signal(verification):
    return any(
        verification.get(name)
        for name in ("tests_run", "invariants", "expected_behavior", "actual_behavior")
    )


class PreconditionsValidator(BaseValidator):
    name = "preconditions"
    subsystem = "preconditions"

    def validate(self, artifact_bundle):
        todo = artifact_bundle["todo"]
        if todo["preconditions"] and not _has_verification_signal(todo["verification"]):
            return ValidationResult.fail(
                code=PRECONDITION_UNCHECKED,
                detail="Preconditions are declared without any verification signal",
                action="Document the verification that checks the stated preconditions",
            )
        return ValidationResult.pass_(code=OK, detail="Preconditions are backed by declared verification signals")
