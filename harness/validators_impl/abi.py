from harness.codes import ABI_LAYOUT_MISMATCH, OK
from harness.validator import BaseValidator, ValidationResult


class AbiValidator(BaseValidator):
    name = "abi"
    subsystem = "abi"

    def validate(self, artifact_bundle):
        abi_changes = [
            path
            for path in artifact_bundle["changed_files"]
            if path.startswith("contracts/") or path.startswith("bindings/")
        ]
        if abi_changes:
            return ValidationResult.fail(
                code=ABI_LAYOUT_MISMATCH,
                detail=f"ABI-surface files changed during harness bootstrap: {abi_changes}",
                action="Keep this bootstrap out of contracts/ and generated bindings/",
            )
        return ValidationResult.pass_(code=OK, detail="No ABI-surface files changed during bootstrap")
