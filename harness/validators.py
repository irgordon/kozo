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
from harness.validators_impl.abi_manifest import AbiManifestValidator
from harness.validators_impl.abi_surface_report import AbiSurfaceReportValidator
from harness.validators_impl.syscall_boundary_contract import SyscallBoundaryContractValidator
from harness.validators_impl.syscall_boundary_conformance import SyscallBoundaryConformanceValidator
from harness.validators_impl.syscall_table_contract import SyscallTableContractValidator
from harness.validators_impl.syscall_class_contract import SyscallClassContractValidator
from harness.validators_impl.syscall_table_conformance import SyscallTableConformanceValidator
from harness.validators_impl.syscall_catalog import SyscallCatalogValidator
from harness.validators_impl.syscall_surface_report import SyscallSurfaceReportValidator
from harness.validators_impl.governance_index_report import GovernanceIndexReportValidator
from harness.validators_impl.protocol_validator import ProtocolContractValidator
from harness.validators_impl.layout_parity import LayoutParityValidator
from harness.validators_impl.entrypoint_validator import ExecutionFoundationValidator
from harness.validators_impl.bridge_validator import BridgeAlignmentValidator
from harness.validators_impl.runtime_trap_path import RuntimeTrapPathValidator
from harness.validators_impl.runtime_smoke_evidence import RuntimeSmokeEvidenceValidator
from harness.validators_impl.runtime_evidence_review import RuntimeEvidenceReviewValidator
from harness.validators_impl.runtime_evidence_taxonomy import RuntimeEvidenceTaxonomyValidator
from harness.validators_impl.runtime_halt_contract import RuntimeHaltContractValidator
from harness.validators_impl.runtime_progression_contract import RuntimeProgressionContractValidator
from harness.validators_impl.runtime_progression_entry_contract import RuntimeProgressionEntryContractValidator
from harness.validators_impl.runtime_progression_evidence import RuntimeProgressionEvidenceValidator
from harness.validators_impl.runtime_progression_stages import RuntimeProgressionStagesValidator
from harness.validators_impl.stack_initialization_evidence_contract import StackInitializationEvidenceContractValidator
from harness.validators_impl.stack_initialization_evidence import StackInitializationEvidenceValidator
from harness.validators_impl.memory_initialization_evidence_contract import MemoryInitializationEvidenceContractValidator
from harness.validators_impl.memory_initialization_evidence import MemoryInitializationEvidenceValidator
from harness.validators_impl.controlled_runtime_loop_contract import ControlledRuntimeLoopContractValidator
from harness.validators_impl.controlled_runtime_loop_evidence import ControlledRuntimeLoopEvidenceValidator
from harness.validators_impl.first_governed_runtime_capability import FirstGovernedRuntimeCapabilityValidator
from harness.validators_impl.first_governed_runtime_capability_evidence import FirstGovernedRuntimeCapabilityEvidenceValidator
from harness.validators_impl.boot_blocker_report import BootBlockerReportValidator
from harness.validators_impl.boot_protocol_decision import BootProtocolDecisionValidator
from harness.validators_impl.boot_image_skeleton import BootImageSkeletonValidator
from harness.validators_impl.boot_image_packaging import BootImagePackagingValidator
from harness.validators_impl.boot_tooling import BootToolingValidator
from harness.validators_impl.kernel_loadability import KernelLoadabilityValidator
from harness.validators_impl.host_dependency_portability import HostDependencyPortabilityValidator
from harness.validators_impl.qemu_smoke_evidence import QemuSmokeEvidenceValidator
from harness.validators_impl.return_path_proof import ReturnPathProofValidator
from harness.validators_impl.execution_proof import ExecutionProofValidator
from harness.validators_impl.validator_coverage import ValidatorCoverageValidator
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
    "abi_manifest": AbiManifestValidator,
    "abi_surface_report": AbiSurfaceReportValidator,
    "syscall_boundary_contract": SyscallBoundaryContractValidator,
    "syscall_boundary_conformance": SyscallBoundaryConformanceValidator,
    "syscall_table_contract": SyscallTableContractValidator,
    "syscall_class_contract": SyscallClassContractValidator,
    "syscall_table_conformance": SyscallTableConformanceValidator,
    "syscall_catalog": SyscallCatalogValidator,
    "syscall_surface_report": SyscallSurfaceReportValidator,
    "governance_index_report": GovernanceIndexReportValidator,
    "protocol_contract_alignment": ProtocolContractValidator,
    "layout_parity": LayoutParityValidator,
    "execution_foundation": ExecutionFoundationValidator,
    "bridge_alignment": BridgeAlignmentValidator,
    "runtime_trap_path": RuntimeTrapPathValidator,
    "runtime_smoke_evidence": RuntimeSmokeEvidenceValidator,
    "runtime_evidence_review": RuntimeEvidenceReviewValidator,
    "runtime_evidence_taxonomy": RuntimeEvidenceTaxonomyValidator,
    "runtime_halt_contract": RuntimeHaltContractValidator,
    "runtime_progression_contract": RuntimeProgressionContractValidator,
    "runtime_progression_entry_contract": RuntimeProgressionEntryContractValidator,
    "runtime_progression_evidence": RuntimeProgressionEvidenceValidator,
    "runtime_progression_stages": RuntimeProgressionStagesValidator,
    "stack_initialization_evidence_contract": StackInitializationEvidenceContractValidator,
    "stack_initialization_evidence": StackInitializationEvidenceValidator,
    "memory_initialization_evidence_contract": MemoryInitializationEvidenceContractValidator,
    "memory_initialization_evidence": MemoryInitializationEvidenceValidator,
    "controlled_runtime_loop_contract": ControlledRuntimeLoopContractValidator,
    "controlled_runtime_loop_evidence": ControlledRuntimeLoopEvidenceValidator,
    "first_governed_runtime_capability": FirstGovernedRuntimeCapabilityValidator,
    "first_governed_runtime_capability_evidence": FirstGovernedRuntimeCapabilityEvidenceValidator,
    "boot_blocker_report": BootBlockerReportValidator,
    "boot_protocol_decision": BootProtocolDecisionValidator,
    "boot_image_skeleton": BootImageSkeletonValidator,
    "boot_image_packaging": BootImagePackagingValidator,
    "boot_tooling": BootToolingValidator,
    "kernel_loadability": KernelLoadabilityValidator,
    "host_dependency_portability": HostDependencyPortabilityValidator,
    "qemu_smoke_evidence": QemuSmokeEvidenceValidator,
    "return_path_proof": ReturnPathProofValidator,
    "execution_proof": ExecutionProofValidator,
    "validator_coverage": ValidatorCoverageValidator,
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
