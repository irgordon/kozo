from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import memory_initialization_evidence_contract as contract_module
from harness.codes import MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_EXPECTED_ARCHITECTURE = "x86_64"
_EXPECTED_RUNTIME_PATH = "boot_smoke_to_stack_memory_and_runtime_progression_to_halt"
_EXPECTED_STAGE = "MEMORY_INITIALIZATION_EVIDENCE"
_EXPECTED_SOURCE_FILE = "kernel/arch/x86_64/boot.asm"
_EXPECTED_REGION_SECTION = ".bss"
_EXPECTED_REGION_START = "boot_memory_region"
_EXPECTED_REGION_END = "boot_memory_region_end"
_EXPECTED_REGION_SIZE = 4096
_EXPECTED_REGION_ALIGNMENT = 4096
_EXPECTED_ALLOCATION_MODE = "static"
_EXPECTED_OWNER = "x86_64 boot memory evidence path"
_EXPECTED_LIFETIME = "entry_to_runtime_progression_and_halt"
_EXPECTED_OPERATION = "zero_fill"
_EXPECTED_COVERAGE = "entire_controlled_region"
_EXPECTED_FILL_VALUE = 0
_EXPECTED_WIDTH = 8
_EXPECTED_PROBE_OFFSET = 0
_EXPECTED_SENTINEL = "0x4b4f5a4f4d454d31"
_EXPECTED_COMPARISON = "exact_readback"
_EXPECTED_PROBE_STEPS = (
    "write_sentinel",
    "read_sentinel",
    "compare_equal",
    "restore_fill_value",
)
_EXPECTED_MARKER = "KOZO_MEMORY_INIT_OK"
_EXPECTED_MARKER_STATUS = "emitted"
_EXPECTED_MARKER_AFTER = (
    "controlled_region_zero_fill",
    "survival_probe_success",
)
_EXPECTED_MARKER_BEFORE = "runtime_progression_entry"
_EXPECTED_FUTURE_VALIDATOR = "memory_initialization_evidence"

_REQUIRED_PREREQUISITES = (
    "QEMU serial smoke evidence",
    "runtime halt contract",
    "runtime progression contract",
    "runtime progression stages contract",
    "stack initialization evidence",
    "stack initialization evidence contract",
)
_REQUIRED_EVIDENCE = (
    "controlled region symbols present in runtime source",
    "entire controlled region zero-filled by runtime code",
    "survival probe writes reads compares and restores the sentinel location",
    "KOZO_MEMORY_INIT_OK marker captured after successful initialization and probe",
    "memory initialization validator proof",
)
_REQUIRED_ASSUMPTIONS_ENABLED = (
    "bounded access to the contract-owned controlled region after the proven memory marker",
    "eligibility for runtime progression entry after separate progression path evidence",
)
_REQUIRED_ASSUMPTIONS_NOT_ENABLED = (
    "physical memory discovery",
    "paging enabled",
    "virtual memory management",
    "memory allocator behavior",
    "heap allocation",
    "complete Odin runtime readiness",
    "interrupt handling",
    "scheduler behavior",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "device driver behavior",
    "syscall dispatch during boot",
    "production readiness",
)
_REQUIRED_NON_GOALS = (
    "general memory management",
    "physical memory discovery",
    "paging implementation",
    "virtual memory management",
    "memory allocator behavior",
    "heap allocation",
    "complete Odin runtime readiness",
    "runtime progression beyond the governed bounded call",
    "halt loop replacement",
    "interrupt handling",
    "scheduler behavior",
    "userspace execution",
    "process model behavior",
    "VFS behavior",
    "device driver behavior",
    "Linux compatibility",
    "POSIX compatibility",
    "production readiness",
)


@dataclass(frozen=True)
class MemoryEvidenceIssue:
    reason: str
    contract_field: str
    detail: str


class MemoryInitializationEvidenceContractValidator(BaseValidator):
    name = "memory_initialization_evidence_contract"
    subsystem = "memory_initialization_evidence_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _memory_evidence_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Memory evidence contract defines the implemented static-region proof boundary",
        )


def _memory_evidence_issue(contract_path: Path) -> MemoryEvidenceIssue | None:
    contract = _load_contract(contract_path)
    if isinstance(contract, MemoryEvidenceIssue):
        return contract
    return _first_issue(
        _current_state_issue(contract),
        _reference_issue(contract),
        _implementation_specification_issue(contract),
        _governance_lists_issue(contract),
    )


def _load_contract(
    path: Path,
) -> contract_module.MemoryInitializationEvidenceContract | MemoryEvidenceIssue:
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Memory evidence contract is missing: {path}")
    try:
        return contract_module.load_memory_initialization_evidence_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Memory evidence contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Memory evidence contract schema violation: {exc}")


def _current_state_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    state = contract.current_state
    return _first_issue(
        _expected_issue(contract.architecture, _EXPECTED_ARCHITECTURE, "wrong_architecture", "architecture"),
        _expected_issue(state.runtime_path, _EXPECTED_RUNTIME_PATH, "wrong_runtime_path", "current_state.runtime_path"),
        _expected_issue(state.stage, _EXPECTED_STAGE, "wrong_stage", "current_state.stage"),
        _implementation_state_issue(state.implemented),
    )


def _implementation_state_issue(implemented: bool) -> MemoryEvidenceIssue | None:
    if implemented is True:
        return None
    return _issue(
        "memory_implementation_missing",
        "current_state.implemented",
        "Memory evidence contract must record the implemented proof path",
    )


def _reference_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    state = contract.current_state
    return _first_issue(
        _contract_reference_issue(state.halt_contract, "current_state.halt_contract"),
        _contract_reference_issue(state.progression_stages_contract, "current_state.progression_stages_contract"),
        _contract_reference_issue(
            state.stack_initialization_evidence_contract,
            "current_state.stack_initialization_evidence_contract",
        ),
    )


def _contract_reference_issue(contract_path: str, field: str) -> MemoryEvidenceIssue | None:
    if contract_module.contract_repo_path(contract_path).is_file():
        return None
    return _issue("missing_contract_reference", field, f"Referenced contract is missing: {contract_path}")


def _implementation_specification_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _controlled_region_issue(contract.controlled_region),
        _initialization_operation_issue(contract.initialization_operation),
        _survival_probe_issue(contract),
        _marker_placement_issue(contract.marker_placement),
    )


def _controlled_region_issue(region: contract_module.ControlledMemoryRegion) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _region_geometry_issue(region),
        _region_location_issue(region),
        _region_capacity_issue(region),
        _region_ownership_issue(region),
    )


def _region_location_issue(region: contract_module.ControlledMemoryRegion) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            region.source_file,
            _EXPECTED_SOURCE_FILE,
            "wrong_region_source",
            "controlled_region.source_file",
        ),
        _expected_issue(region.section, _EXPECTED_REGION_SECTION, "wrong_region_section", "controlled_region.section"),
        _expected_issue(
            region.start_symbol,
            _EXPECTED_REGION_START,
            "wrong_region_start_symbol",
            "controlled_region.start_symbol",
        ),
        _expected_issue(
            region.end_symbol,
            _EXPECTED_REGION_END,
            "wrong_region_end_symbol",
            "controlled_region.end_symbol",
        ),
    )


def _region_capacity_issue(region: contract_module.ControlledMemoryRegion) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(region.size_bytes, _EXPECTED_REGION_SIZE, "wrong_region_size", "controlled_region.size_bytes"),
        _expected_issue(
            region.alignment_bytes,
            _EXPECTED_REGION_ALIGNMENT,
            "wrong_region_alignment",
            "controlled_region.alignment_bytes",
        ),
    )


def _region_ownership_issue(region: contract_module.ControlledMemoryRegion) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            region.allocation_mode,
            _EXPECTED_ALLOCATION_MODE,
            "wrong_allocation_mode",
            "controlled_region.allocation_mode",
        ),
        _expected_issue(region.owner, _EXPECTED_OWNER, "wrong_region_owner", "controlled_region.owner"),
        _expected_issue(region.lifetime, _EXPECTED_LIFETIME, "wrong_region_lifetime", "controlled_region.lifetime"),
    )


def _region_geometry_issue(region: contract_module.ControlledMemoryRegion) -> MemoryEvidenceIssue | None:
    alignment = region.alignment_bytes
    if alignment & (alignment - 1):
        return _issue(
            "invalid_region_geometry",
            "controlled_region.alignment_bytes",
            "Region alignment must be a power of two",
        )
    if region.size_bytes % alignment:
        return _issue(
            "invalid_region_geometry",
            "controlled_region.size_bytes",
            "Region size must be a multiple of its alignment",
        )
    return None


def _initialization_operation_issue(
    operation: contract_module.InitializationOperation,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _initialization_semantics_issue(operation),
        _initialization_order_issue(operation),
    )


def _initialization_semantics_issue(
    operation: contract_module.InitializationOperation,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            operation.operation,
            _EXPECTED_OPERATION,
            "wrong_initialization_operation",
            "initialization_operation.operation",
        ),
        _expected_issue(
            operation.coverage,
            _EXPECTED_COVERAGE,
            "incomplete_initialization_coverage",
            "initialization_operation.coverage",
        ),
        _expected_issue(
            operation.fill_value,
            _EXPECTED_FILL_VALUE,
            "wrong_fill_value",
            "initialization_operation.fill_value",
        ),
    )


def _initialization_order_issue(
    operation: contract_module.InitializationOperation,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            operation.width_bytes,
            _EXPECTED_WIDTH,
            "wrong_initialization_width",
            "initialization_operation.width_bytes",
        ),
        _required_true_issue(
            operation.required_before_probe,
            "initialization_before_probe_missing",
            "initialization_operation.required_before_probe",
        ),
    )


def _survival_probe_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    probe = contract.survival_probe
    return _first_issue(
        _probe_geometry_issue(contract),
        _probe_value_issue(probe),
        _probe_order_issue(probe),
    )


def _probe_value_issue(probe: contract_module.SurvivalProbe) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            probe.offset_bytes,
            _EXPECTED_PROBE_OFFSET,
            "wrong_probe_offset",
            "survival_probe.offset_bytes",
        ),
        _expected_issue(
            probe.write_width_bytes,
            _EXPECTED_WIDTH,
            "wrong_probe_width",
            "survival_probe.write_width_bytes",
        ),
        _expected_issue(
            probe.sentinel_value,
            _EXPECTED_SENTINEL,
            "wrong_probe_sentinel",
            "survival_probe.sentinel_value",
        ),
        _expected_issue(probe.comparison, _EXPECTED_COMPARISON, "wrong_probe_comparison", "survival_probe.comparison"),
    )


def _probe_order_issue(probe: contract_module.SurvivalProbe) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            probe.required_steps,
            _EXPECTED_PROBE_STEPS,
            "wrong_probe_steps",
            "survival_probe.required_steps",
        ),
        _required_true_issue(
            probe.required_before_marker,
            "probe_before_marker_missing",
            "survival_probe.required_before_marker",
        ),
    )


def _probe_geometry_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    probe = contract.survival_probe
    if probe.offset_bytes % probe.write_width_bytes:
        return _issue(
            "invalid_probe_geometry",
            "survival_probe.offset_bytes",
            "Probe offset must align to the write width",
        )
    if probe.offset_bytes + probe.write_width_bytes > contract.controlled_region.size_bytes:
        return _issue(
            "probe_out_of_bounds",
            "survival_probe.offset_bytes",
            "Probe must stay inside the controlled region",
        )
    return None


def _marker_placement_issue(marker: contract_module.MarkerPlacement) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _marker_identity_issue(marker),
        _marker_order_issue(marker),
        _marker_ownership_issue(marker),
    )


def _marker_identity_issue(marker: contract_module.MarkerPlacement) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(marker.reserved_marker, _EXPECTED_MARKER, "missing_marker", "marker_placement.reserved_marker"),
        _expected_issue(
            marker.marker_status,
            _EXPECTED_MARKER_STATUS,
            "wrong_marker_status",
            "marker_placement.marker_status",
        ),
        _marker_emission_issue(marker.marker_emitted),
    )


def _marker_order_issue(marker: contract_module.MarkerPlacement) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            marker.required_after,
            _EXPECTED_MARKER_AFTER,
            "wrong_marker_predecessors",
            "marker_placement.required_after",
        ),
        _expected_issue(
            marker.required_before,
            _EXPECTED_MARKER_BEFORE,
            "wrong_marker_successor",
            "marker_placement.required_before",
        ),
    )


def _marker_ownership_issue(marker: contract_module.MarkerPlacement) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _expected_issue(
            marker.emission_owner,
            _EXPECTED_OWNER,
            "wrong_marker_owner",
            "marker_placement.emission_owner",
        ),
    )


def _marker_emission_issue(emitted: bool) -> MemoryEvidenceIssue | None:
    if emitted is True:
        return None
    return _issue("marker_not_emitted", "marker_placement.marker_emitted", "KOZO_MEMORY_INIT_OK must be emitted by the governed memory evidence path")


def _governance_lists_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _proof_requirements_issue(contract),
        _assumption_boundary_issue(contract),
        _validator_and_non_goals_issue(contract),
    )


def _proof_requirements_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _required_values_issue(
            contract.prerequisites,
            _REQUIRED_PREREQUISITES,
            "missing_prerequisite",
            "prerequisites",
        ),
        _required_values_issue(
            contract.evidence_requirements,
            _REQUIRED_EVIDENCE,
            "missing_evidence_requirement",
            "evidence_requirements",
        ),
    )


def _assumption_boundary_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _required_values_issue(
            contract.assumptions_enabled,
            _REQUIRED_ASSUMPTIONS_ENABLED,
            "missing_assumption_mapping",
            "assumptions_enabled",
        ),
        _required_values_issue(
            contract.assumptions_not_enabled,
            _REQUIRED_ASSUMPTIONS_NOT_ENABLED,
            "missing_assumption_boundary",
            "assumptions_not_enabled",
        ),
    )


def _validator_and_non_goals_issue(
    contract: contract_module.MemoryInitializationEvidenceContract,
) -> MemoryEvidenceIssue | None:
    return _first_issue(
        _required_values_issue(
            contract.future_validators,
            (_EXPECTED_FUTURE_VALIDATOR,),
            "missing_future_validator",
            "future_validators",
        ),
        _required_values_issue(contract.non_goals, _REQUIRED_NON_GOALS, "missing_non_goal", "non_goals"),
    )


def _required_values_issue(
    actual_values: tuple[str, ...],
    expected_values: tuple[str, ...],
    reason: str,
    field: str,
) -> MemoryEvidenceIssue | None:
    for expected in expected_values:
        if expected not in actual_values:
            detail = f"Memory initialization evidence contract must declare: {expected}"
            return _issue(reason, f"{field}.{expected}", detail)
    return None


def _expected_issue(actual, expected, reason: str, field: str) -> MemoryEvidenceIssue | None:
    if actual == expected:
        return None
    return _issue(reason, field, f"Expected {field} to be {expected}, got {actual}")


def _required_true_issue(actual: bool, reason: str, field: str) -> MemoryEvidenceIssue | None:
    if actual is True:
        return None
    return _issue(reason, field, f"Expected {field} to be true")


def _first_issue(*issues: MemoryEvidenceIssue | None) -> MemoryEvidenceIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> MemoryEvidenceIssue:
    return MemoryEvidenceIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: MemoryEvidenceIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=MEMORY_INITIALIZATION_EVIDENCE_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep memory evidence aligned with the implemented static-region proof boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
