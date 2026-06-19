from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from harness.codes import OK, VALIDATOR_COVERAGE_INVALID
from harness.registry import CHECKS
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_TESTS_DIR = _ROOT / "tests"
_NEGATIVE_TEST_MARKERS = (
    "missing",
    "invalid",
    "wrong",
    "fails",
    "failure",
    "out_of_order",
    "dead",
    "unrelated",
    "rejects",
)


@dataclass(frozen=True)
class ValidatorTestContract:
    validator_name: str
    test_path: Path
    coverage_token: str
    required_negative_markers: tuple[str, ...]


@dataclass(frozen=True)
class CoverageIssue:
    reason: str
    validator_name: str
    detail: str
    marker_name: str = ""


@dataclass(frozen=True)
class TestFileAnalysis:
    source: str
    tree: ast.Module | None
    test_functions: tuple[ast.FunctionDef, ...]
    helper_functions: tuple[ast.FunctionDef, ...]
    negative_coverage: dict[str, dict[str, str]]


_VALIDATOR_TEST_CONTRACTS = {
    "schema": ValidatorTestContract("schema", _TESTS_DIR / "test_schema.py", "SchemaValidator", ("missing_required_schema_fields",)),
    "plan_lifecycle": ValidatorTestContract("plan_lifecycle", _TESTS_DIR / "test_plan_lifecycle.py", "PlanLifecycleValidator", ("out_of_order_step_ids",)),
    "step_scope": ValidatorTestContract("step_scope", _TESTS_DIR / "test_step_scope.py", "StepScopeValidator", ("outside_task_scope",)),
    "verification_refs": ValidatorTestContract("verification_refs", _TESTS_DIR / "test_verification_refs.py", "VerificationRefsValidator", ("invalid_verification_ref",)),
    "explanation": ValidatorTestContract("explanation", _TESTS_DIR / "test_explanation.py", "ExplanationValidator", ("missing_explanation_summary",)),
    "preconditions": ValidatorTestContract("preconditions", _TESTS_DIR / "test_preconditions.py", "PreconditionsValidator", ("missing_verification_signal",)),
    "subagent": ValidatorTestContract("subagent", _TESTS_DIR / "test_subagent.py", "SubagentValidator", ("subagent_scope_declared",)),
    "rust": ValidatorTestContract("rust", _TESTS_DIR / "test_rust.py", "RustValidator", ("missing_cargo_evidence",)),
    "odin": ValidatorTestContract("odin", _TESTS_DIR / "test_odin.py", "OdinValidator", ("missing_odin_check_evidence",)),
    "abi": ValidatorTestContract("abi", _TESTS_DIR / "test_abi.py", "AbiValidator", ("missing_generated_binding",)),
    "abi_manifest": ValidatorTestContract(
        "abi_manifest",
        _TESTS_DIR / "test_abi_manifest.py",
        "AbiManifestValidator",
        (
            "missing_manifest_file",
            "invalid_json",
            "schema_violation",
            "missing_generated_binding_path",
            "syscall_constant_mismatch",
            "missing_status_syscall_constant",
            "layout_field_offset_mismatch",
            "diagnostic_names_manifest_field",
        ),
    ),
    "abi_surface_report": ValidatorTestContract(
        "abi_surface_report",
        _TESTS_DIR / "test_abi_surface_report.py",
        "AbiSurfaceReportValidator",
        (
            "missing_report_file",
            "stale_report_content",
            "manual_edit_detected",
            "missing_status_constant",
            "missing_syscall_constant",
            "missing_binding_path",
            "missing_layout_field",
            "missing_layout_size_alignment",
            "missing_request_sentinel",
            "missing_response_sentinel",
            "manifest_change_updates_report",
            "diagnostic_names_report_field",
        ),
    ),
    "syscall_boundary_contract": ValidatorTestContract(
        "syscall_boundary_contract",
        _TESTS_DIR / "test_syscall_boundary_contract.py",
        "SyscallBoundaryContractValidator",
        (
            "missing_contract_file",
            "invalid_json",
            "schema_violation",
            "wrong_architecture",
            "missing_assembly_path",
            "wrong_entry_symbol",
            "wrong_syscall_id_register",
            "wrong_payload_register",
            "wrong_return_register",
            "missing_abi_syscall_constant",
            "missing_nop_syscall_constant",
            "wrong_nop_payload_argument",
            "wrong_nop_return_status",
            "nop_mutates_payload",
            "missing_payload_layout",
            "request_sentinel_mismatch",
            "response_sentinel_mismatch",
            "unknown_status_constant",
            "unknown_mutable_field",
            "payload_retention_forbidden",
            "unknown_proof_validator",
            "diagnostic_names_contract_field",
        ),
    ),
    "syscall_boundary_conformance": ValidatorTestContract(
        "syscall_boundary_conformance",
        _TESTS_DIR / "test_syscall_boundary_conformance.py",
        "SyscallBoundaryConformanceValidator",
        (
            "missing_assembly_entry_symbol",
            "wrong_dispatcher_symbol",
            "wrong_syscall_id_register",
            "wrong_payload_register",
            "rust_extern_symbol_mismatch",
            "rust_wrong_syscall_constant",
            "rust_request_sentinel_mismatch",
            "rust_response_validation_mismatch",
            "odin_dispatcher_symbol_mismatch",
            "odin_wrong_syscall_constant",
            "odin_null_payload_invalid_return_mismatch",
            "odin_bad_sequence_invalid_return_mismatch",
            "odin_unknown_mutated_field",
            "odin_response_sentinel_mismatch",
            "odin_success_return_mismatch",
            "unknown_proof_validator",
            "diagnostic_names_contract_field",
        ),
    ),
    "syscall_table_contract": ValidatorTestContract(
        "syscall_table_contract",
        _TESTS_DIR / "test_syscall_table_contract.py",
        "SyscallTableContractValidator",
        (
            "missing_contract_file",
            "invalid_json",
            "schema_violation",
            "wrong_architecture",
            "missing_dispatcher_source",
            "wrong_dispatcher_symbol",
            "missing_abi_syscall_constant",
            "missing_payload_layout",
            "missing_branch_selector",
            "wrong_branch_mapping",
            "missing_unknown_syscall_branch",
            "wrong_unknown_syscall_return",
            "unknown_path_mutates_payload",
            "missing_nop_syscall_constant",
            "missing_status_syscall",
            "missing_status_syscall_constant",
            "no_payload_payload_layout_reference",
            "no_payload_missing_return_status",
            "wrong_no_payload_return_status",
            "no_payload_mutates_payload",
            "no_payload_uses_payload_layout",
            "status_payload_layout_reference",
            "status_wrong_return_status",
            "status_mutates_payload",
            "status_uses_payload_layout",
            "diagnostic_names_contract_field",
        ),
    ),
    "syscall_class_contract": ValidatorTestContract(
        "syscall_class_contract",
        _TESTS_DIR / "test_syscall_class_contract.py",
        "SyscallClassContractValidator",
        (
            "missing_contract_file",
            "invalid_json",
            "schema_violation",
            "missing_no_payload_status_class",
            "missing_payload_mutating_status_class",
            "malformed_no_payload_status",
            "malformed_payload_mutating_status",
            "unknown_example_syscall",
            "missing_syscall_class",
            "unknown_syscall_class",
            "nop_wrong_class",
            "status_wrong_class",
            "heartbeat_wrong_class",
            "kind_class_mismatch",
            "no_payload_has_layout",
            "no_payload_has_request",
            "no_payload_has_response",
            "no_payload_mutates_payload",
            "status_payload_layout_reference",
            "status_mutates_payload",
            "payload_missing_layout",
            "payload_missing_request",
            "payload_missing_response",
            "payload_unknown_mutation_field",
            "diagnostic_names_class_field",
        ),
    ),
    "syscall_table_conformance": ValidatorTestContract(
        "syscall_table_conformance",
        _TESTS_DIR / "test_syscall_table_conformance.py",
        "SyscallTableConformanceValidator",
        (
            "missing_dispatcher_source",
            "missing_dispatcher_symbol",
            "syscall_id_type_mismatch",
            "return_type_mismatch",
            "missing_valid_syscall_branch",
            "hardcoded_branch_selector",
            "wrong_branch_body",
            "extra_uncontracted_branch",
            "payload_layout_mismatch",
            "missing_unknown_branch",
            "wrong_unknown_return_status",
            "unknown_path_mutates_payload",
            "unknown_path_calls_heartbeat_logic",
            "unknown_path_unreachable",
            "missing_abi_syscall_constant",
            "missing_abi_payload_layout",
            "missing_nop_branch",
            "missing_status_branch",
            "nop_hardcoded_selector",
            "status_hardcoded_selector",
            "wrong_nop_return_status",
            "wrong_status_return_status",
            "nop_mutates_payload",
            "status_mutates_payload",
            "nop_uses_payload_layout",
            "status_uses_payload_layout",
            "missing_nop_abi_constant",
            "missing_status_abi_constant",
            "diagnostic_names_contract_field",
        ),
    ),
    "syscall_catalog": ValidatorTestContract(
        "syscall_catalog",
        _TESTS_DIR / "test_syscall_catalog.py",
        "SyscallCatalogValidator",
        (
            "missing_catalog_file",
            "invalid_json",
            "schema_violation",
            "missing_table_entry",
            "unknown_catalog_syscall",
            "constant_mismatch",
            "numeric_id_mismatch",
            "kind_mismatch",
            "class_mismatch",
            "payload_behavior_mismatch",
            "return_status_mismatch",
            "mutation_behavior_mismatch",
            "branch_selector_mismatch",
            "unknown_proof_validator",
            "missing_required_class_proof",
            "runtime_probe_true_but_missing",
            "runtime_probe_false_but_present",
            "diagnostic_names_catalog_field",
        ),
    ),
    "syscall_surface_report": ValidatorTestContract(
        "syscall_surface_report",
        _TESTS_DIR / "test_syscall_surface_report.py",
        "SyscallSurfaceReportValidator",
        (
            "missing_report_file",
            "stale_report_content",
            "manual_edit_detected",
            "missing_syscall",
            "missing_syscall_class",
            "missing_source_reference",
            "catalog_change_updates_report",
            "diagnostic_names_report_field",
        ),
    ),
    "governance_index_report": ValidatorTestContract(
        "governance_index_report",
        _TESTS_DIR / "test_governance_index_report.py",
        "GovernanceIndexReportValidator",
        (
            "missing_index_file",
            "stale_index_content",
            "manual_edit_detected",
            "missing_current_version",
            "missing_verification_status",
            "missing_registered_validator",
            "missing_active_contract",
            "missing_schema",
            "missing_syscall_report_reference",
            "missing_abi_report_reference",
            "missing_latest_proof_artifact",
            "missing_non_goal",
            "latest_verify_change_updates_report",
            "registry_change_updates_report",
            "diagnostic_names_index_field",
        ),
    ),
    "protocol_contract_alignment": ValidatorTestContract(
        "protocol_contract_alignment",
        _TESTS_DIR / "test_protocol_contract_alignment.py",
        "ProtocolContractValidator",
        (
            "missing_manifest_syscall_constant",
            "missing_status_manifest_syscall_constant",
            "manifest_syscall_value_mismatch",
            "missing_rust_syscall_constant",
            "missing_status_rust_syscall_constant",
            "missing_odin_syscall_constant",
            "missing_status_odin_syscall_constant",
            "rust_hardcoded_syscall_id",
            "rust_hardcoded_status_syscall_id",
            "odin_hardcoded_syscall_id",
            "constant_mismatch",
            "dead_or_stale_constant",
            "diagnostic_names_protocol_field",
        ),
    ),
    "layout_parity": ValidatorTestContract(
        "layout_parity",
        _TESTS_DIR / "test_layout_parity.py",
        "LayoutParityValidator",
        (
            "missing_field",
            "missing_manifest_layout_field",
            "manifest_layout_mismatch",
            "wrong_field_order",
            "wrong_rust_field_width",
            "wrong_odin_field_width",
            "wrong_rust_offset",
            "wrong_odin_offset",
            "wrong_struct_size",
            "dead_or_stale_struct",
            "diagnostic_names_layout_field",
        ),
    ),
    "execution_foundation": ValidatorTestContract(
        "execution_foundation",
        _TESTS_DIR / "test_execution_foundation.py",
        "ExecutionFoundationValidator",
        ("missing_boot_start_symbol",),
    ),
    "bridge_alignment": ValidatorTestContract(
        "bridge_alignment",
        _TESTS_DIR / "test_bridge_alignment.py",
        "BridgeAlignmentValidator",
        (
            "dead_snippets_outside_entry",
            "out_of_order_anchors",
            "missing_dispatcher_handoff",
            "missing_odin_dispatcher_signature",
            "missing_entry_block",
        ),
    ),
    "runtime_trap_path": ValidatorTestContract(
        "runtime_trap_path",
        _TESTS_DIR / "test_runtime_trap_path.py",
        "RuntimeTrapPathValidator",
        (
            "dead_extern_call_outside_helper",
            "missing_payload_construction",
            "wrong_sequence_sentinel",
            "wrong_timestamp_sentinel",
            "wrong_status_bits_initialization",
            "out_of_order_live_path",
            "missing_heartbeat_block",
            "missing_nop_block",
            "missing_status_block",
            "nop_hardcoded_syscall_id",
            "status_hardcoded_syscall_id",
            "nop_non_null_payload",
            "status_non_null_payload",
            "missing_nop_return_validation",
            "missing_status_return_validation",
            "nop_payload_usage",
            "status_payload_usage",
            "nop_not_invoked",
            "status_not_invoked",
        ),
    ),
    "runtime_smoke_evidence": ValidatorTestContract(
        "runtime_smoke_evidence",
        _TESTS_DIR / "test_runtime_smoke_evidence.py",
        "RuntimeSmokeEvidenceValidator",
        (
            "missing_runtime_artifact",
            "empty_runtime_artifact",
            "missing_expected_marker",
            "failure_marker_present",
            "malformed_runtime_metadata",
            "missing_release_evidence_reference",
            "diagnostic_names_runtime_field",
            "missing_metadata",
            "invalid_metadata_json",
            "wrong_evidence_type",
            "metadata_artifact_mismatch",
            "metadata_generated_by_mismatch",
            "metadata_validator_mismatch",
            "metadata_missing_proves_claim",
            "metadata_missing_non_goal",
            "missing_release_metadata_reference",
            "diagnostic_names_metadata_field",
        ),
    ),
    "runtime_evidence_review": ValidatorTestContract(
        "runtime_evidence_review",
        _TESTS_DIR / "test_runtime_evidence_review.py",
        "RuntimeEvidenceReviewValidator",
        (
            "missing_review_document",
            "missing_evidence_type",
            "missing_live_log_path",
            "missing_live_metadata_path",
            "missing_release_bundle_path",
            "missing_validator_reference",
            "missing_qemu_boot_non_goal",
            "missing_hardware_trap_non_goal",
            "missing_linux_non_goal",
            "missing_userspace_non_goal",
            "missing_process_vfs_scheduler_elf_fd_non_goals",
            "missing_production_non_goal",
            "missing_release_evidence_link",
            "missing_release_checklist_gate",
            "metadata_review_non_goal_mismatch",
            "diagnostic_names_review_field",
        ),
    ),
    "boot_blocker_report": ValidatorTestContract(
        "boot_blocker_report",
        _TESTS_DIR / "test_boot_blocker_report.py",
        "BootBlockerReportValidator",
        (
            "missing_report",
            "invalid_report_json",
            "field_mismatch",
            "missing_component",
            "missing_current_surface",
            "missing_non_claim",
            "missing_documentation_reference",
            "diagnostic_names_boot_blocker_field",
        ),
    ),
    "boot_protocol_decision": ValidatorTestContract(
        "boot_protocol_decision",
        _TESTS_DIR / "test_boot_protocol_decision.py",
        "BootProtocolDecisionValidator",
        (
            "missing_adr",
            "wrong_protocol",
            "missing_alternative",
            "missing_non_goal",
            "missing_boot_blocker_reduced_statement",
            "missing_v032_next_phase",
            "diagnostic_names_decision_field",
        ),
    ),
    "boot_image_skeleton": ValidatorTestContract(
        "boot_image_skeleton",
        _TESTS_DIR / "test_boot_image_skeleton.py",
        "BootImageSkeletonValidator",
        (
            "missing_linker_script",
            "missing_limine_config",
            "missing_build_script",
            "missing_boot_image_doc",
            "blocker_state_mismatch",
            "diagnostic_names_field",
        ),
    ),
    "boot_image_packaging": ValidatorTestContract(
        "boot_image_packaging",
        _TESTS_DIR / "test_boot_image_packaging.py",
        "BootImagePackagingValidator",
        (
            "missing_image",
            "missing_metadata",
            "invalid_metadata",
            "wrong_boot_protocol",
            "wrong_image_type",
            "wrong_architecture",
            "image_path_mismatch",
            "missing_non_goal",
            "blocker_state_mismatch",
            "diagnostic_names_field",
        ),
    ),
    "boot_tooling": ValidatorTestContract(
        "boot_tooling",
        _TESTS_DIR / "test_boot_tooling.py",
        "BootToolingValidator",
        (
            "missing_limine_doc",
            "missing_xorriso_doc",
            "missing_ci_install_path",
            "missing_local_install_path",
            "missing_provenance",
            "blocker_mismatch",
            "diagnostic_names_field",
        ),
    ),
    "return_path_proof": ValidatorTestContract(
        "return_path_proof",
        _TESTS_DIR / "test_return_path_proof.py",
        "ReturnPathProofValidator",
        (
            "missing_rust_status_bits_check",
            "missing_odin_status_bits_write",
            "status_bits_diagnostic",
            "unrelated_status_bits_text",
        ),
    ),
    "execution_proof": ValidatorTestContract(
        "execution_proof",
        _TESTS_DIR / "test_execution_proof.py",
        "ExecutionProofValidator",
        (
            "missing_nil_guard",
            "missing_heartbeat_branch",
            "dead_mutations_outside_branch",
            "out_of_order_mutations",
            "missing_status_bits_mutation",
            "missing_serial_observation",
            "status_bits_diagnostic",
        ),
    ),
    "validator_coverage": ValidatorTestContract(
        "validator_coverage",
        _TESTS_DIR / "test_validator_coverage.py",
        "ValidatorCoverageValidator",
        (
            "missing_test_file",
            "missing_coverage_mapping",
            "missing_negative_test",
            "placeholder_negative_rejected",
            "missing_failure_assertion",
            "missing_validator_invocation",
            "token_outside_negative_test",
            "missing_coverage_metadata",
            "missing_required_marker",
            "unknown_marker",
            "mapped_test_missing",
            "mapped_test_placeholder",
            "mapped_test_missing_failure_assertion",
            "mapped_test_missing_validator_invocation",
            "diagnostic_names_requirement",
        ),
    ),
    "evidence": ValidatorTestContract("evidence", _TESTS_DIR / "test_evidence.py", "EvidenceValidator", ("missing_evidence_file",)),
}


def registered_validator_names() -> tuple[str, ...]:
    return tuple(CHECKS.keys())


def validator_coverage_contracts() -> tuple[ValidatorTestContract, ...]:
    return tuple(_VALIDATOR_TEST_CONTRACTS.values())


def expected_test_path_for_validator(name: str) -> Path:
    return _VALIDATOR_TEST_CONTRACTS[name].test_path


def test_file_exists(path: Path) -> bool:
    return path.is_file()


def test_file_has_negative_case(path: Path) -> bool:
    analysis = _analyze_test_file(path)
    return any(_is_negative_test(function, analysis, "") for function in analysis.test_functions)


def find_coverage_issues(
    registered_names: tuple[str, ...],
    contracts: tuple[ValidatorTestContract, ...],
) -> tuple[CoverageIssue, ...]:
    return (
        *_registry_contract_issues(registered_names, contracts),
        *_test_contract_issues(contracts),
    )


def build_coverage_diagnostics(issue: CoverageIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=VALIDATOR_COVERAGE_INVALID,
        detail=f"Validator coverage invalid: {issue.reason}: {issue.validator_name}: {issue.detail}",
        action="Add focused tests with at least one named negative-path test for every registered validator",
        meta={
            "reason": issue.reason,
            "validator_name": issue.validator_name,
            "marker_name": issue.marker_name,
        },
    )


class ValidatorCoverageValidator(BaseValidator):
    name = "validator_coverage"
    subsystem = "validator_coverage"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issues = find_coverage_issues(
            registered_validator_names(),
            validator_coverage_contracts(),
        )
        if issues:
            return build_coverage_diagnostics(issues[0])
        return ValidationResult.pass_(
            code=OK,
            detail="Every registered validator has focused test coverage with at least one negative-path test",
        )


def _registry_contract_issues(
    registered_names: tuple[str, ...],
    contracts: tuple[ValidatorTestContract, ...],
) -> tuple[CoverageIssue, ...]:
    contract_names = tuple(contract.validator_name for contract in contracts)
    return (
        *_missing_coverage_map_issues(registered_names, contract_names),
        *_extra_coverage_map_issues(registered_names, contract_names),
    )


def _missing_coverage_map_issues(
    registered_names: tuple[str, ...],
    contract_names: tuple[str, ...],
) -> tuple[CoverageIssue, ...]:
    return tuple(
        CoverageIssue(
            "missing_coverage_mapping",
            name,
            "registered validator is not represented in the coverage contract map",
        )
        for name in registered_names
        if name not in contract_names
    )


def _extra_coverage_map_issues(
    registered_names: tuple[str, ...],
    contract_names: tuple[str, ...],
) -> tuple[CoverageIssue, ...]:
    return tuple(
        CoverageIssue(
            "unknown_coverage_mapping",
            name,
            "coverage contract references a validator that is not registered",
        )
        for name in contract_names
        if name not in registered_names
    )


def _test_contract_issues(contracts: tuple[ValidatorTestContract, ...]) -> tuple[CoverageIssue, ...]:
    issues: list[CoverageIssue] = []
    for contract in contracts:
        issue = _test_contract_issue(contract)
        if issue is not None:
            issues.append(issue)
    return tuple(issues)


def _test_contract_issue(contract: ValidatorTestContract) -> CoverageIssue | None:
    if not test_file_exists(contract.test_path):
        return CoverageIssue("missing_test_file", contract.validator_name, _relative_test_path(contract))
    analysis = _analyze_test_file(contract.test_path)
    if contract.coverage_token not in analysis.source:
        return CoverageIssue("missing_validator_invocation", contract.validator_name, contract.coverage_token)
    return _negative_coverage_issue(contract, analysis) or _marker_coverage_issue(contract, analysis)


def _negative_coverage_issue(
    contract: ValidatorTestContract,
    analysis: TestFileAnalysis,
) -> CoverageIssue | None:
    candidates = tuple(
        function
        for function in analysis.test_functions
        if _is_negative_test_name(function.name)
    )
    if not candidates:
        return CoverageIssue("missing_negative_test", contract.validator_name, _relative_test_path(contract))
    if any(_is_negative_test(function, analysis, contract.coverage_token) for function in candidates):
        return None
    return _negative_candidate_issue(contract, analysis, candidates)


def _negative_candidate_issue(
    contract: ValidatorTestContract,
    analysis: TestFileAnalysis,
    candidates: tuple[ast.FunctionDef, ...],
) -> CoverageIssue:
    if not any(_function_invokes_validator(function, analysis) for function in candidates):
        return CoverageIssue("negative_test_missing_validator_invocation", contract.validator_name, _relative_test_path(contract))
    if not any(_function_asserts_failure(function) for function in candidates):
        return CoverageIssue("negative_test_missing_failure_assertion", contract.validator_name, _relative_test_path(contract))
    if not any(_candidate_references_token(function, analysis, contract.coverage_token) for function in candidates):
        return CoverageIssue("coverage_token_outside_negative_test", contract.validator_name, contract.coverage_token)
    return None


def _marker_coverage_issue(
    contract: ValidatorTestContract,
    analysis: TestFileAnalysis,
) -> CoverageIssue | None:
    metadata = analysis.negative_coverage.get(contract.validator_name)
    if metadata is None:
        return CoverageIssue("missing_coverage_metadata", contract.validator_name, "KOZO_NEGATIVE_COVERAGE")
    required_markers = set(contract.required_negative_markers)
    declared_markers = set(metadata)
    missing_markers = sorted(required_markers - declared_markers)
    if missing_markers:
        return _marker_issue("missing_required_marker", contract, missing_markers[0])
    unknown_markers = sorted(declared_markers - required_markers)
    if unknown_markers:
        return _marker_issue("unknown_marker", contract, unknown_markers[0])
    return _mapped_negative_test_issue(contract, analysis, metadata)


def _mapped_negative_test_issue(
    contract: ValidatorTestContract,
    analysis: TestFileAnalysis,
    metadata: dict[str, str],
) -> CoverageIssue | None:
    functions = {function.name: function for function in analysis.test_functions}
    for marker in contract.required_negative_markers:
        test_name = metadata[marker]
        function = functions.get(test_name)
        if function is None:
            return _marker_issue("mapped_test_function_missing", contract, marker)
        if not _is_negative_test(function, analysis, contract.coverage_token):
            return _marker_issue("mapped_test_not_behavioral_negative", contract, marker)
    return None


def _marker_issue(reason: str, contract: ValidatorTestContract, marker: str) -> CoverageIssue:
    return CoverageIssue(
        reason,
        contract.validator_name,
        f"{marker} in {_relative_test_path(contract)}",
        marker,
    )


def _relative_test_path(contract: ValidatorTestContract) -> str:
    try:
        return str(contract.test_path.relative_to(_ROOT))
    except ValueError:
        return str(contract.test_path)


def _analyze_test_file(path: Path) -> TestFileAnalysis:
    source = path.read_text()
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return TestFileAnalysis(source, None, (), (), {})
    return TestFileAnalysis(
        source,
        tree,
        _test_functions(tree),
        _validator_helper_functions(tree),
        _negative_coverage_metadata(tree),
    )


def _test_functions(tree: ast.Module) -> tuple[ast.FunctionDef, ...]:
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


def _negative_coverage_metadata(tree: ast.Module) -> dict[str, dict[str, str]]:
    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if not any(_assignment_target_name(target) == "KOZO_NEGATIVE_COVERAGE" for target in statement.targets):
            continue
        try:
            value = ast.literal_eval(statement.value)
        except (ValueError, SyntaxError):
            return {}
        return _normalize_negative_coverage_metadata(value)
    return {}


def _assignment_target_name(target: ast.AST) -> str:
    return target.id if isinstance(target, ast.Name) else ""


def _normalize_negative_coverage_metadata(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, str]] = {}
    for validator_name, marker_map in value.items():
        if not isinstance(validator_name, str) or not isinstance(marker_map, dict):
            continue
        normalized[validator_name] = {
            marker: test_name
            for marker, test_name in marker_map.items()
            if isinstance(marker, str) and isinstance(test_name, str)
        }
    return normalized


def _is_negative_test_name(name: str) -> bool:
    return any(marker in name for marker in _NEGATIVE_TEST_MARKERS)


def _is_negative_test(
    function: ast.FunctionDef,
    analysis: TestFileAnalysis,
    coverage_token: str,
) -> bool:
    return (
        _is_negative_test_name(function.name)
        and _candidate_references_token(function, analysis, coverage_token)
        and _function_invokes_validator(function, analysis)
        and _function_asserts_failure(function)
    )


def _candidate_references_token(
    function: ast.FunctionDef,
    analysis: TestFileAnalysis,
    coverage_token: str,
) -> bool:
    return (
        _node_contains_token(function, analysis.source, coverage_token)
        or _function_calls_tokened_validator_helper(function, analysis, coverage_token)
    )


def _node_contains_token(node: ast.AST, source: str, token: str) -> bool:
    if not token:
        return True
    segment = ast.get_source_segment(source, node)
    return segment is not None and token in segment


def _function_invokes_validator(function: ast.FunctionDef, analysis: TestFileAnalysis) -> bool:
    return (
        _function_invokes_validator_directly(function)
        or _function_calls_validator_helper(function, _helper_names(analysis.helper_functions))
    )


def _function_invokes_validator_directly(function: ast.FunctionDef) -> bool:
    return any(
        _is_validate_call(node) or _is_run_aggregator_call(node)
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    )


def _function_calls_validator_helper(
    function: ast.FunctionDef,
    helper_names: tuple[str, ...],
) -> bool:
    return any(
        _call_name(node) in helper_names
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
    )


def _function_calls_tokened_validator_helper(
    function: ast.FunctionDef,
    analysis: TestFileAnalysis,
    coverage_token: str,
) -> bool:
    helper_names = tuple(
        helper.name
        for helper in analysis.helper_functions
        if _node_contains_token(helper, analysis.source, coverage_token)
    )
    return _function_calls_validator_helper(function, helper_names)


def _validator_helper_functions(tree: ast.Module) -> tuple[ast.FunctionDef, ...]:
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("test_")
        and _function_invokes_validator_directly(node)
    )


def _helper_names(helpers: tuple[ast.FunctionDef, ...]) -> tuple[str, ...]:
    return tuple(helper.name for helper in helpers)


def _function_asserts_failure(function: ast.FunctionDef) -> bool:
    return any(_is_failure_assertion(node) for node in ast.walk(function))


def _is_validate_call(call: ast.Call) -> bool:
    return isinstance(call.func, ast.Attribute) and call.func.attr == "validate"


def _is_run_aggregator_call(call: ast.Call) -> bool:
    return _call_name(call) == "run_aggregator"


def _call_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return ""


def _is_failure_assertion(node: ast.AST) -> bool:
    return (
        _is_unittest_failure_assertion(node)
        or _is_plain_failure_assert(node)
        or _is_diagnostic_assertion(node)
    )


def _is_unittest_failure_assertion(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr == "assertEqual":
        return _call_args_reference_failure(node)
    if node.func.attr == "assertNotEqual":
        return _call_args_reference_non_pass(node)
    if node.func.attr in ("assertIn", "assertRegex"):
        return _call_args_reference_diagnostic(node)
    return False


def _is_plain_failure_assert(node: ast.AST) -> bool:
    return isinstance(node, ast.Assert) and _comparison_references_failure(node.test)


def _is_diagnostic_assertion(node: ast.AST) -> bool:
    return _node_references_failure_code(node) or _node_references_diagnostic_field(node)


def _call_args_reference_failure(call: ast.Call) -> bool:
    return (
        len(call.args) >= 2
        and _node_references_status(call.args[0])
        and _node_has_constant(call.args[1], "fail")
    ) or _node_references_failure_code(call)


def _call_args_reference_non_pass(call: ast.Call) -> bool:
    return (
        len(call.args) >= 2
        and _node_references_status(call.args[0])
        and _node_has_constant(call.args[1], "pass")
    )


def _call_args_reference_diagnostic(call: ast.Call) -> bool:
    return any(
        _node_references_diagnostic_field(argument) or _node_references_failure_code(argument)
        for argument in call.args
    )


def _comparison_references_failure(node: ast.AST) -> bool:
    if not isinstance(node, ast.Compare):
        return False
    left_and_comparators = (node.left, *node.comparators)
    if any(_node_references_failure_code(item) for item in left_and_comparators):
        return True
    return any(
        _is_status_failure_comparison(node.left, operator, comparator)
        for operator, comparator in zip(node.ops, node.comparators)
    )


def _is_status_failure_comparison(left: ast.AST, operator: ast.cmpop, right: ast.AST) -> bool:
    return (
        _node_references_status(left)
        and isinstance(operator, ast.Eq)
        and _node_has_constant(right, "fail")
    ) or (
        _node_references_status(left)
        and isinstance(operator, ast.NotEq)
        and _node_has_constant(right, "pass")
    )


def _node_references_status(node: ast.AST) -> bool:
    return isinstance(node, ast.Attribute) and node.attr == "status"


def _node_references_failure_code(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Name)
        and child.id.endswith("_INVALID")
        for child in ast.walk(node)
    )


def _node_references_diagnostic_field(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Constant)
        and child.value in ("contract_field", "reason", "code", "missing_anchor", "validator_name")
        for child in ast.walk(node)
    )


def _node_has_constant(node: ast.AST, value: str) -> bool:
    return isinstance(node, ast.Constant) and node.value == value
