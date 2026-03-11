from pathlib import Path

from harness.codes import EVIDENCE_FILE_MISSING, OK
from harness.validator import BaseValidator, ValidationResult


class EvidenceValidator(BaseValidator):
    name = "evidence"
    subsystem = "evidence"

    def validate(self, artifact_bundle):
        root_dir = artifact_bundle.get("root_dir")
        if not isinstance(root_dir, str) or not root_dir:
            return ValidationResult.fail(
                code=EVIDENCE_FILE_MISSING,
                detail="Validation bundle does not declare root_dir",
                action="Pass the repository root into the aggregator bundle",
            )
        root = Path(root_dir)
        for relative_path in artifact_bundle["evidence_files"]:
            if not (root / relative_path).is_file():
                return ValidationResult.fail(
                    code=EVIDENCE_FILE_MISSING,
                    detail=f"Evidence file {relative_path} is missing on disk",
                    action="Regenerate or remove stale evidence paths before verification",
                )
        return ValidationResult.pass_(code=OK, detail="Evidence file references resolve on disk")
