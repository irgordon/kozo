from harness.codes import ODIN_CHECK_FAILED, OK
from harness.validator import BaseValidator, ValidationResult


class OdinValidator(BaseValidator):
    name = "odin"
    subsystem = "odin"

    def validate(self, artifact_bundle):
        odin_changes = [
            path
            for path in artifact_bundle["changed_files"]
            if path.endswith(".odin") or path.startswith("kernel/") or path.startswith("bindings/odin/")
        ]
        if odin_changes:
            return ValidationResult.fail(
                code=ODIN_CHECK_FAILED,
                detail=f"Odin-relevant changes require explicit odin check coverage: {odin_changes}",
                action="Keep this bootstrap scoped away from kernel sources or add odin verification evidence",
            )
        return ValidationResult.pass_(code=OK, detail="No Odin kernel changes require validation in this bootstrap loop")
