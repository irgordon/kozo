from types import MappingProxyType
from harness.registry import SUBSYSTEMS

CODES = MappingProxyType({
    "OK": "Operation succeeded",
    "SCHEMA_INVALID": "Artifact failed JSON schema validation",
    "PLAN_STATUS_INVALID": "Illegal plan status transition",
    "STEP_ORDER_INVALID": "Step ordering violated",
    "STEP_FAILURE_THRESHOLD": "Step failure threshold exceeded",
    "REPLAN_REQUIRED": "Execution halted pending replan",
    "STEP_SCOPE_UNPLANNED_FILE": "Changed file outside step scope",
    "STEP_SCOPE_EMPTY_DONE_STEP": "Completed step produced no file effects",
    "STEP_SCOPE_OUTSIDE_TASK_SCOPE": "Step scope outside task scope",
    "VERIFICATION_REFS_INVALID": "Invalid verification reference",
    "MISSING_REF": "Verification reference points to missing entry",
    "EXPLANATION_SUMMARY_REQUIRED": "Explanation summary required but missing",
    "PRECONDITION_UNCHECKED": "Precondition lacks verification",
    "SUBAGENT_SCOPE_VIOLATION": "Subagent modified files outside scope",
    "RUST_FMT_FAILED": "cargo fmt failed",
    "RUST_CLIPPY_FAILED": "cargo clippy failed",
    "RUST_TEST_FAILED": "cargo test failed",
    "ODIN_CHECK_FAILED": "odin check failed",
    "ABI_WIDTH_MISMATCH": "ABI width mismatch",
    "ABI_LAYOUT_MISMATCH": "ABI layout mismatch",
    "EVIDENCE_FILE_MISSING": "Required evidence file missing",
})

OK = "OK"