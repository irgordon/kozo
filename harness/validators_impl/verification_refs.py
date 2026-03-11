import re

from harness.codes import MISSING_REF, OK, VERIFICATION_REFS_INVALID
from harness.invariants import VERIFICATION_REF_PATTERN, get_predicate
from harness.validator import BaseValidator, ValidationResult

_verification_ref = get_predicate("verification_ref")
_verification_ref_re = re.compile(VERIFICATION_REF_PATTERN)


def _resolve_ref(verification, ref):
    match = _verification_ref_re.fullmatch(ref)
    if match is None:
        raise ValueError(ref)
    prefix, index = ref.split("[", 1)
    section = prefix.split(".", 1)[1]
    return verification.get(section), int(index[:-1]), section


class VerificationRefsValidator(BaseValidator):
    name = "verification_refs"
    subsystem = "verification_refs"

    def validate(self, artifact_bundle):
        verification = artifact_bundle["todo"]["verification"]
        for step in artifact_bundle["todo"]["steps"]:
            for ref in step["verification_refs"]:
                if not _verification_ref(ref):
                    return ValidationResult.fail(
                        code=VERIFICATION_REFS_INVALID,
                        detail=f"Invalid verification ref {ref!r}",
                        action="Use refs that satisfy harness/invariants.py",
                    )
                target, index, section = _resolve_ref(verification, ref)
                if not isinstance(target, list) or index >= len(target):
                    return ValidationResult.fail(
                        code=MISSING_REF,
                        detail=f"Verification ref {ref!r} does not resolve into verification.{section}",
                        action="Point each step verification ref at an existing verification entry",
                    )
        return ValidationResult.pass_(code=OK, detail="Verification refs resolve into canonical verification entries")
