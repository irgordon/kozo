from __future__ import annotations
from typing import Dict, Tuple, Type

from harness.registry import CHECKS
from harness.validator import BaseValidator

from harness.validators_impl.schema import SchemaValidator
from harness.validators_impl.plan_lifecycle import PlanLifecycleValidator
from harness.validators_impl.step_scope import StepScopeValidator
from harness.validators_impl.verification_refs import VerificationRefsValidator
from harness.validators_impl.explanation import ExplanationValidator
from harness.validators_impl.preconditions import PreconditionsValidator
from harness.validators_impl.subagent import SubagentValidator
from harness.validators_impl.rust import RustValidator
from harness.validators_impl.odin import OdinValidator
from harness.validators_impl.abi import AbiValidator
from harness.validators_impl.evidence import EvidenceValidator

_VALIDATOR_CLASSES_BY_NAME: Dict[str, Type[BaseValidator]] = {
    "schema": SchemaValidator,
    "plan_lifecycle": PlanLifecycleValidator,
    "step_scope": StepScopeValidator,
    "verification_refs": VerificationRefsValidator,
    "explanation": ExplanationValidator,
    "preconditions": PreconditionsValidator,
    "subagent": SubagentValidator,
    "rust": RustValidator,
    "odin": OdinValidator,
    "abi": AbiValidator,
    "evidence": EvidenceValidator,
}

if tuple(_VALIDATOR_CLASSES_BY_NAME.keys()) != tuple(CHECKS.keys()):
    raise ValueError("Validator registry must be declared in canonical CHECKS order")

def _build_validators() -> Tuple[Type[BaseValidator], ...]:
    canonical_names = tuple(CHECKS.keys())
    registered_names = tuple(_VALIDATOR_CLASSES_BY_NAME.keys())

    missing = sorted(set(canonical_names) - set(registered_names))
    extra = sorted(set(registered_names) - set(canonical_names))

    if missing:
        raise ValueError(f"Validator registry missing canonical validators: {missing}")
    if extra:
        raise ValueError(f"Validator registry contains non-canonical validators: {extra}")

    ordered = []
    for name in canonical_names:
        cls = _VALIDATOR_CLASSES_BY_NAME[name]
        validator_name = getattr(cls, "name", None)
        validator_subsystem = getattr(cls, "subsystem", None)

        if validator_name != name:
            raise ValueError(
                f"Validator class {cls.__name__} must declare name={name!r}, got {validator_name!r}"
            )

        expected_subsystem = CHECKS[name]
        if validator_subsystem != expected_subsystem:
            raise ValueError(
                f"Validator class {cls.__name__} must declare subsystem={expected_subsystem!r}, got {validator_subsystem!r}"
            )

        if not hasattr(cls, "validate"):
            raise ValueError(f"Validator class {cls.__name__} does not define validate(...)")

        ordered.append(cls)

    return tuple(ordered)

VALIDATORS = _build_validators()
