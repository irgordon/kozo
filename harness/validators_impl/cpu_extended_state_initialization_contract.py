from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness import cpu_extended_state_initialization_contract as contract_module
from harness.codes import CPU_EXTENDED_STATE_INITIALIZATION_CONTRACT_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_EXPECTED_FEATURE_BITS = (("FPU", 0), ("FXSR", 24), ("SSE", 25), ("SSE2", 26))
_EXPECTED_CR0_SET = (("MP", 1), ("NE", 5))
_EXPECTED_CR0_CLEAR = (("EM", 2), ("TS", 3))
_EXPECTED_CR4_SET = (("OSFXSR", 9), ("OSXMMEXCPT", 10))
_EXPECTED_CR4_CLEAR = (("OSXSAVE", 18),)
_EXPECTED_MARKERS = (
    "KOZO_CPU_EXT_STATE_INIT_START",
    "KOZO_CPU_EXT_STATE_INIT_OK",
    "KOZO_SIMD_PROBE_OK",
)
_EXPECTED_STATUSES = {
    "success": 0,
    "cpuid_unavailable": 1,
    "required_feature_missing": 2,
    "control_configuration_failed": 3,
    "x87_initialization_failed": 4,
    "sse_initialization_failed": 5,
    "simd_probe_failed": 6,
}
_REQUIRED_NON_GOALS = (
    "AVX",
    "AVX2",
    "AVX-512",
    "OSXSAVE enablement",
    "XCR0 configuration",
    "XSAVE and XRSTOR",
    "extended-state context switching",
    "scheduler behavior",
    "interrupt handling",
    "exception recovery",
    "userspace execution",
    "production readiness",
)


@dataclass(frozen=True)
class CpuExtendedStateContractIssue:
    reason: str
    contract_field: str
    detail: str


class CpuExtendedStateInitializationContractValidator(BaseValidator):
    name = "cpu_extended_state_initialization_contract"
    subsystem = "cpu_extended_state_initialization_contract"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="CPU extended-state contract governs pre-Odin x87 and SSE initialization",
        )


def _contract_issue(path: Path) -> CpuExtendedStateContractIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, CpuExtendedStateContractIssue):
        return contract
    return _first_issue(
        _execution_point_issue(contract),
        _cpu_feature_issue(contract),
        _control_policy_issue(contract),
        _state_initialization_issue(contract),
        _probe_issue(contract),
        _marker_and_status_issue(contract),
        _avx_policy_issue(contract),
        _claim_boundary_issue(contract),
    )


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"CPU extended-state contract is missing: {path}")
    try:
        return contract_module.load_cpu_extended_state_initialization_contract(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"CPU extended-state contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"CPU extended-state contract schema violation: {exc}")


def _execution_point_issue(contract) -> CpuExtendedStateContractIssue | None:
    point = contract.execution_point
    expected = {
        "source_file": "kernel/arch/x86_64/boot.asm",
        "entry_symbol": "_start",
        "required_after_marker": "KOZO_MEMORY_INIT_OK",
        "required_before_symbol": "runtime_progression_entry",
    }
    return _mapping_issue(point, expected, "invalid_execution_point", "execution_point")


def _cpu_feature_issue(contract) -> CpuExtendedStateContractIssue | None:
    features = contract.required_cpu_features
    return _first_issue(
        _mapping_issue(
            features,
            {
                "maximum_basic_leaf_query": 0,
                "required_leaf": 1,
                "leaf_1_register": "edx",
                "required_mask": "0x07000001",
            },
            "missing_required_cpu_feature",
            "required_cpu_features",
        ),
        _bit_list_issue(features.get("required_bits"), _EXPECTED_FEATURE_BITS, "missing_required_cpu_feature", "required_cpu_features.required_bits"),
    )


def _control_policy_issue(contract) -> CpuExtendedStateContractIssue | None:
    return _first_issue(
        _one_control_policy_issue(contract.cr0_policy, _EXPECTED_CR0_SET, _EXPECTED_CR0_CLEAR, "cr0_policy"),
        _one_control_policy_issue(contract.cr4_policy, _EXPECTED_CR4_SET, _EXPECTED_CR4_CLEAR, "cr4_policy"),
    )


def _one_control_policy_issue(policy, set_bits, clear_bits, field) -> CpuExtendedStateContractIssue | None:
    return _first_issue(
        _mapping_issue(policy, {"read_modify_write": True, "readback_required": True}, "invalid_control_policy", field),
        _bit_list_issue(policy.get("required_set_bits"), set_bits, "invalid_control_policy", f"{field}.required_set_bits"),
        _bit_list_issue(policy.get("required_clear_bits"), clear_bits, "invalid_control_policy", f"{field}.required_clear_bits"),
    )


def _state_initialization_issue(contract) -> CpuExtendedStateContractIssue | None:
    return _first_issue(
        _mapping_issue(
            contract.x87_initialization,
            {
                "operation": "fninit",
                "observation_operation": "fnstcw",
                "expected_control_word": "0x037f",
            },
            "invalid_x87_policy",
            "x87_initialization",
        ),
        _mapping_issue(
            contract.sse_initialization,
            {
                "load_operation": "ldmxcsr",
                "observation_operation": "stmxcsr",
                "expected_mxcsr": "0x00001f80",
            },
            "invalid_sse_policy",
            "sse_initialization",
        ),
    )


def _probe_issue(contract) -> CpuExtendedStateContractIssue | None:
    expected = {
        "operation": "pxor",
        "width_bytes": 16,
        "buffer_size_bytes": 16,
        "buffer_alignment_bytes": 16,
        "expected_low": "0xffee2233bbaa6677",
        "expected_high": "0x8796a5b4c3d2e1f0",
        "scalar_result_validation": True,
        "output_restored_to_zero": True,
        "xmm_register_cleared": True,
    }
    return _mapping_issue(contract.simd_probe, expected, "invalid_probe_geometry", "simd_probe")


def _marker_and_status_issue(contract) -> CpuExtendedStateContractIssue | None:
    if contract.success_markers != _EXPECTED_MARKERS:
        return _issue("wrong_marker_order", "success_markers", "CPU extended-state markers must use the governed order")
    if contract.failure_statuses != _EXPECTED_STATUSES:
        return _issue("invalid_failure_status", "failure_statuses", "CPU extended-state statuses must remain exact")
    continuation = contract.runtime_continuation
    if continuation.get("runtime_entry_requires_simd_marker") is not True:
        return _issue("invalid_runtime_continuation", "runtime_continuation.runtime_entry_requires_simd_marker", "Odin entry must require SIMD evidence")
    return None


def _avx_policy_issue(contract) -> CpuExtendedStateContractIssue | None:
    policy = contract.avx_prohibition
    expected = {
        "cr4_osxsave_required_value": 0,
        "xsetbv_allowed": False,
        "xgetbv_required": False,
    }
    issue = _mapping_issue(policy, expected, "avx_not_prohibited", "avx_prohibition")
    if issue is not None:
        return issue
    for value in ("ymm", "zmm"):
        if value not in policy.get("forbidden_register_classes", []):
            return _issue("avx_not_prohibited", "avx_prohibition.forbidden_register_classes", f"AVX policy must forbid {value}")
    return None


def _claim_boundary_issue(contract) -> CpuExtendedStateContractIssue | None:
    for claim in ("AVX support", "XSAVE support", "per-task extended-state ownership", "production readiness"):
        if claim not in contract.claim_boundary.get("does_not_prove", ()):
            return _issue("invalid_claim_boundary", "claim_boundary.does_not_prove", f"Claim boundary must exclude {claim}")
    for non_goal in _REQUIRED_NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"Contract must retain non-goal: {non_goal}")
    return None


def _mapping_issue(actual: dict[str, Any], expected: dict[str, Any], reason: str, field: str):
    for key, value in expected.items():
        if actual.get(key) != value:
            return _issue(reason, f"{field}.{key}", f"Expected {field}.{key} to be {value}")
    return None


def _bit_list_issue(actual, expected, reason: str, field: str):
    pairs = tuple((item.get("name"), item.get("bit")) for item in actual or () if isinstance(item, dict))
    if pairs == expected:
        return None
    return _issue(reason, field, f"Expected {field} to be {expected}")


def _first_issue(*issues):
    return next((issue for issue in issues if issue is not None), None)


def _issue(reason: str, field: str, detail: str) -> CpuExtendedStateContractIssue:
    return CpuExtendedStateContractIssue(reason, field, detail)


def _failure(issue: CpuExtendedStateContractIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=CPU_EXTENDED_STATE_INITIALIZATION_CONTRACT_INVALID,
        detail=issue.detail,
        action="Keep the CPU extended-state contract aligned with the pre-Odin x87 and SSE boundary",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
