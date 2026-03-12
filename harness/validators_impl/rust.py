from harness.codes import OK, RUST_TEST_FAILED
from harness.validator import BaseValidator, ValidationResult

_RUST_SUFFIXES = (".rs",)
_RUST_PATHS = ("Cargo.toml", "Cargo.lock", "bindings/rust/")


class RustValidator(BaseValidator):
    name = "rust"
    subsystem = "rust"

    def validate(self, artifact_bundle):
        todo = artifact_bundle["todo"]
        changed_files = artifact_bundle["changed_files"]
        rust_changes = [
            path
            for path in changed_files
            if path.endswith(_RUST_SUFFIXES) or path in _RUST_PATHS[:2] or path.startswith(_RUST_PATHS[2])
        ]
        if not rust_changes:
            return ValidationResult.pass_(code=OK, detail="No Rust changes require validation in this bootstrap loop")

        declared_cargo_check = any(
            test["command"].startswith("cargo check ")
            for test in todo["verification"]["tests_run"]
        )
        declared_logs = set(todo["verification"]["logs"])
        has_rust_evidence = any(path in declared_logs for path in artifact_bundle["evidence_files"])

        if not declared_cargo_check or not has_rust_evidence:
            return ValidationResult.fail(
                code=RUST_TEST_FAILED,
                detail=f"Rust-relevant changes require explicit Rust verification: {rust_changes}",
                action="Keep this bootstrap scoped to harness and Odin-adjacent files or add Rust verification evidence",
            )
        return ValidationResult.pass_(code=OK, detail="Rust changes are backed by declared cargo check evidence")
