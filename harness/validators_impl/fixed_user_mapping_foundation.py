from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness import fixed_user_mapping_foundation as contract_module
from harness.codes import FIXED_USER_MAPPING_FOUNDATION_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_CONTRACT_PATH = contract_module.CONTRACT_PATH
_PAGE_TABLES = (
    "governed_pml4",
    "governed_kernel_pdpt",
    "governed_kernel_pd",
    "governed_kernel_pt",
    "governed_user_pdpt",
    "governed_user_pd",
    "governed_user_pt",
)
_USER_REGIONS = (
    ("user_probe_code", 0x0000400000000000, False, True),
    ("user_probe_data", 0x0000400000001000, True, False),
    ("user_probe_stack", 0x0000400000002000, True, False),
)
_MARKERS = (
    "KOZO_USER_MAPPING_INIT_START",
    "KOZO_USER_MAPPING_TABLES_OK",
    "KOZO_USER_MAPPING_PERMISSIONS_OK",
    "KOZO_USER_MAPPING_ACTIVATE_OK",
    "KOZO_USER_MAPPING_SURVIVAL_OK",
)
_STATUSES = {
    "success": 0,
    "paging_mode_unsupported": 1,
    "nx_unavailable": 2,
    "physical_backing_invalid": 3,
    "table_geometry_invalid": 4,
    "overlap": 5,
    "permission_invalid": 6,
    "cr3_activation_failed": 7,
    "survival_failed": 8,
}
_NON_GOALS = (
    "Ring 3 execution",
    "GDT user descriptors",
    "TSS",
    "IDT",
    "syscall MSRs",
    "general userspace execution",
    "process isolation",
    "general virtual memory manager",
    "dynamic mapping",
    "frame allocator",
    "page-fault recovery",
    "scheduler behavior",
    "production readiness",
)


@dataclass(frozen=True)
class FixedUserMappingIssue:
    reason: str
    contract_field: str
    detail: str


class FixedUserMappingFoundationValidator(BaseValidator):
    name = "fixed_user_mapping_foundation"
    subsystem = "fixed_user_mapping_foundation"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _contract_issue(_CONTRACT_PATH)
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Fixed user-mapping contract governs one four-level W^X mapping foundation",
        )


def _contract_issue(path: Path) -> FixedUserMappingIssue | None:
    contract = _load_contract(path)
    if isinstance(contract, FixedUserMappingIssue):
        return contract
    checks = (
        _paging_issue,
        _table_issue,
        _kernel_policy_issue,
        _user_geometry_issue,
        _permission_policy_issue,
        _activation_issue,
        _walk_and_survival_issue,
        _marker_and_status_issue,
        _claim_issue,
    )
    for check in checks:
        issue = check(contract)
        if issue is not None:
            return issue
    return None


def _load_contract(path: Path):
    if not path.is_file():
        return _issue("missing_contract_file", "contract", f"Fixed user-mapping contract is missing: {path}")
    try:
        return contract_module.load_fixed_user_mapping_foundation(path)
    except json.JSONDecodeError as exc:
        return _issue("invalid_contract_json", "contract", f"Fixed user-mapping contract is invalid JSON: {exc}")
    except (KeyError, TypeError, ValueError) as exc:
        return _issue("contract_schema_violation", "contract", f"Fixed user-mapping schema violation: {exc}")


def _paging_issue(contract) -> FixedUserMappingIssue | None:
    expected = {
        "mode": "four_level",
        "page_size_bytes": 4096,
        "la57_required": False,
        "nx_required": True,
        "efer_nxe_required": True,
        "physical_address_source": "limine_executable_address_response",
        "uniform_kernel_load_offset_required": True,
    }
    if contract.paging != expected:
        return _issue("invalid_page_size", "paging", "Paging must use four levels, 4 KiB pages, active NX, and Limine executable-address backing")
    return None


def _table_issue(contract) -> FixedUserMappingIssue | None:
    tables = contract.page_tables
    if (
        tables.get("root_symbol") != "governed_pml4"
        or tables.get("page_count") != 7
        or tables.get("size_bytes") != 7 * 4096
        or tables.get("alignment_bytes") != 4096
        or tables.get("zero_fill_required") is not True
        or tuple(tables.get("pages", ())) != _PAGE_TABLES
    ):
        return _issue("invalid_table_geometry", "page_tables", "Fixed page-table storage must contain seven aligned, explicitly cleared pages")
    return None


def _kernel_policy_issue(contract) -> FixedUserMappingIssue | None:
    names = {region["name"] for region in contract.kernel_regions}
    required = {"kernel_text", "kernel_rodata", "kernel_data", "kernel_bss", "page_table_storage"}
    if names != required:
        return _issue("missing_kernel_region", "kernel_regions", "All required supervisor kernel regions must be declared")
    if any(region["user"] for region in contract.kernel_regions):
        return _issue("kernel_user_accessible", "kernel_regions.user", "No preserved kernel region may be user-accessible")
    if any(region["writable"] and region["executable"] for region in contract.kernel_regions):
        return _issue("write_execute_violation", "kernel_regions", "Kernel contract mappings must preserve W^X")
    return None


def _user_geometry_issue(contract) -> FixedUserMappingIssue | None:
    if len(contract.user_regions) != len(_USER_REGIONS):
        return _issue("missing_user_region", "user_regions", "Exactly one code, data, and stack page must be declared")
    intervals = [
        (_address(region.get("virtual_start")), _address(region.get("virtual_end")))
        for region in contract.user_regions
    ]
    for index, (start, end) in enumerate(intervals):
        name = _USER_REGIONS[index][0]
        if start % 4096 or end % 4096 or end - start != 4096:
            return _issue("misaligned_backing", f"user_regions.{name}", "Each user region must be one aligned page")
    if any(_overlap(left, right) for index, left in enumerate(intervals) for right in intervals[index + 1:]):
        return _issue("overlapping_user_regions", "user_regions", "Fixed user regions must not overlap")
    for region, expected in zip(contract.user_regions, _USER_REGIONS):
        name, address, writable, executable = expected
        start = _address(region.get("virtual_start"))
        end = _address(region.get("virtual_end"))
        if region.get("name") != name or start != address:
            return _issue("noncanonical_virtual_address", f"user_regions.{name}", "User virtual addresses must match the fixed canonical layout")
        if not _is_lower_canonical(start) or not _is_lower_canonical(end - 1):
            return _issue("noncanonical_virtual_address", f"user_regions.{name}", "User regions must remain in the lower canonical half")
        if region.get("user") is not True:
            return _issue("missing_user_permission", f"user_regions.{name}.user", "Every fixed user region must require U/S propagation")
        if (region.get("writable"), region.get("executable")) != (writable, executable):
            return _issue("invalid_user_permissions", f"user_regions.{name}", "User code must be RX and user data/stack must be RW-NX")
    return None


def _permission_policy_issue(contract) -> FixedUserMappingIssue | None:
    policy = contract.permission_policy
    if tuple(policy.get("user_levels", ())) != ("PML4E", "PDPTE", "PDE", "PTE"):
        return _issue("missing_user_propagation", "permission_policy.user_levels", "U/S must propagate through all four translation levels")
    required_true = (
        "dedicated_user_subtree_required",
        "kernel_supervisor_only",
        "write_xor_execute_required",
        "page_tables_supervisor_only",
        "effective_permissions_combine_all_levels",
    )
    if any(policy.get(field) is not True for field in required_true):
        return _issue("missing_wx_rule", "permission_policy", "Permission policy must require a dedicated user subtree, supervisor kernel, and effective W^X")
    return None


def _activation_issue(contract) -> FixedUserMappingIssue | None:
    activation = contract.activation
    required_true = (
        "construction_precedes_policy_validation",
        "policy_validation_precedes_cr3_load",
        "readback_required",
        "exact_root_match_required",
        "mov_cr3_is_serializing",
    )
    if any(activation.get(field) is not True for field in required_true):
        return _issue("invalid_activation_policy", "activation", "CR3 activation must follow policy validation and require exact readback")
    if activation.get("cr3_address_mask") != "0x000ffffffffff000":
        return _issue("invalid_activation_policy", "activation.cr3_address_mask", "CR3 comparison must use the governed physical-address mask")
    return None


def _walk_and_survival_issue(contract) -> FixedUserMappingIssue | None:
    walk = contract.software_walk
    if walk.get("symbol") != "walk_page_mapping" or walk.get("fixed_table_storage_only") is not True:
        return _issue("missing_software_walk", "software_walk", "Software walk must resolve only fixed table storage")
    survival = contract.survival_probe
    required_true = (
        "kernel_static_value_checked",
        "kernel_stack_checked",
        "serial_continuation_checked",
        "user_data_write_read_restore",
        "user_stack_write_read_restore",
        "post_activation_walk_required",
        "ring3_execution_forbidden",
    )
    if any(survival.get(field) is not True for field in required_true):
        return _issue("missing_survival_requirement", "survival_probe", "Survival proof must cover kernel, stack, user pages, post-walk, and exclude Ring 3")
    return None


def _marker_and_status_issue(contract) -> FixedUserMappingIssue | None:
    if contract.success_markers != _MARKERS:
        return _issue("invalid_marker_order", "success_markers", "User-mapping success markers must use the governed order")
    if contract.failure_statuses != _STATUSES:
        return _issue("invalid_status_map", "failure_statuses", "User-mapping statuses must use exact values 0 through 8")
    return None


def _claim_issue(contract) -> FixedUserMappingIssue | None:
    for non_goal in _NON_GOALS:
        if non_goal not in contract.non_goals:
            return _issue("missing_non_goal", f"non_goals.{non_goal}", f"Fixed user mapping must preserve non-goal: {non_goal}")
    if "Ring 3 execution" not in contract.claim_boundary.get("does_not_prove", ()):
        return _issue("invalid_claim_boundary", "claim_boundary.does_not_prove", "The contract must not claim Ring 3 execution")
    return None


def _address(value) -> int:
    if not isinstance(value, str):
        return -1
    try:
        return int(value, 16)
    except ValueError:
        return -1


def _is_lower_canonical(address: int) -> bool:
    return 0 <= address < 0x0000800000000000


def _overlap(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _issue(reason: str, field: str, detail: str) -> FixedUserMappingIssue:
    return FixedUserMappingIssue(reason, field, detail)


def _failure(issue: FixedUserMappingIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=FIXED_USER_MAPPING_FOUNDATION_INVALID,
        detail=issue.detail,
        action="Align the fixed user-mapping contract with its one static four-level mapping foundation",
        meta={"reason": issue.reason, "contract_field": issue.contract_field},
    )
