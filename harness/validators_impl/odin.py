from harness.codes import ODIN_CHECK_FAILED, OK
from harness.validator import BaseValidator, ValidationResult


def _odin_changes(changed_files):
    return [
        path
        for path in changed_files
        if path.endswith(".odin") or path.startswith("kernel/") or path.startswith("bindings/odin/")
    ]


def _declares_odin_check(todo):
    for test in todo["verification"]["tests_run"]:
        if test["command"].startswith("odin check "):
            return True
    return False


def _has_odin_evidence(todo, evidence_files):
    declared_logs = set(todo["verification"]["logs"])
    return any(path in declared_logs for path in evidence_files)


class OdinValidator(BaseValidator):
    name = "odin"
    subsystem = "odin"

    def validate(self, artifact_bundle):
        todo = artifact_bundle["todo"]
        odin_changes = _odin_changes(artifact_bundle["changed_files"])
        if not odin_changes:
            return ValidationResult.pass_(code=OK, detail="No Odin kernel changes require validation in this bootstrap loop")
        if not _declares_odin_check(todo) or not _has_odin_evidence(todo, artifact_bundle["evidence_files"]):
            return ValidationResult.fail(
                code=ODIN_CHECK_FAILED,
                detail=f"Odin-relevant changes require explicit odin check coverage: {odin_changes}",
                action="Keep this bootstrap scoped away from kernel sources or add odin verification evidence",
            )
        return ValidationResult.pass_(code=OK, detail="Odin changes are backed by declared odin check evidence")
