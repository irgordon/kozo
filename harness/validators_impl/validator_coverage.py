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


@dataclass(frozen=True)
class CoverageIssue:
    reason: str
    validator_name: str
    detail: str


@dataclass(frozen=True)
class TestFileAnalysis:
    source: str
    tree: ast.Module | None
    test_functions: tuple[ast.FunctionDef, ...]
    helper_functions: tuple[ast.FunctionDef, ...]


_VALIDATOR_TEST_CONTRACTS = {
    "schema": ValidatorTestContract("schema", _TESTS_DIR / "test_schema.py", "SchemaValidator"),
    "plan_lifecycle": ValidatorTestContract("plan_lifecycle", _TESTS_DIR / "test_plan_lifecycle.py", "PlanLifecycleValidator"),
    "step_scope": ValidatorTestContract("step_scope", _TESTS_DIR / "test_step_scope.py", "StepScopeValidator"),
    "verification_refs": ValidatorTestContract("verification_refs", _TESTS_DIR / "test_verification_refs.py", "VerificationRefsValidator"),
    "explanation": ValidatorTestContract("explanation", _TESTS_DIR / "test_explanation.py", "ExplanationValidator"),
    "preconditions": ValidatorTestContract("preconditions", _TESTS_DIR / "test_preconditions.py", "PreconditionsValidator"),
    "subagent": ValidatorTestContract("subagent", _TESTS_DIR / "test_subagent.py", "SubagentValidator"),
    "rust": ValidatorTestContract("rust", _TESTS_DIR / "test_rust.py", "RustValidator"),
    "odin": ValidatorTestContract("odin", _TESTS_DIR / "test_odin.py", "OdinValidator"),
    "abi": ValidatorTestContract("abi", _TESTS_DIR / "test_abi.py", "AbiValidator"),
    "protocol_contract_alignment": ValidatorTestContract(
        "protocol_contract_alignment",
        _TESTS_DIR / "test_protocol_contract_alignment.py",
        "ProtocolContractValidator",
    ),
    "layout_parity": ValidatorTestContract("layout_parity", _TESTS_DIR / "test_layout_parity.py", "LayoutParityValidator"),
    "execution_foundation": ValidatorTestContract(
        "execution_foundation",
        _TESTS_DIR / "test_execution_foundation.py",
        "ExecutionFoundationValidator",
    ),
    "bridge_alignment": ValidatorTestContract("bridge_alignment", _TESTS_DIR / "test_bridge_alignment.py", "BridgeAlignmentValidator"),
    "runtime_trap_path": ValidatorTestContract("runtime_trap_path", _TESTS_DIR / "test_runtime_trap_path.py", "RuntimeTrapPathValidator"),
    "return_path_proof": ValidatorTestContract("return_path_proof", _TESTS_DIR / "test_return_path_proof.py", "ReturnPathProofValidator"),
    "execution_proof": ValidatorTestContract("execution_proof", _TESTS_DIR / "test_execution_proof.py", "ExecutionProofValidator"),
    "validator_coverage": ValidatorTestContract("validator_coverage", _TESTS_DIR / "test_validator_coverage.py", "ValidatorCoverageValidator"),
    "evidence": ValidatorTestContract("evidence", _TESTS_DIR / "test_evidence.py", "EvidenceValidator"),
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
        meta={"reason": issue.reason, "validator_name": issue.validator_name},
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
    return _negative_coverage_issue(contract, analysis)


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
        return TestFileAnalysis(source, None, (), ())
    return TestFileAnalysis(
        source,
        tree,
        _test_functions(tree),
        _validator_helper_functions(tree),
    )


def _test_functions(tree: ast.Module) -> tuple[ast.FunctionDef, ...]:
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )


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
