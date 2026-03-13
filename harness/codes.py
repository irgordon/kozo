from types import MappingProxyType

from harness.registry import FAIL, PASS

OK = "OK"
SCHEMA_INVALID = "SCHEMA_INVALID"
PLAN_STATUS_INVALID = "PLAN_STATUS_INVALID"
STEP_ORDER_INVALID = "STEP_ORDER_INVALID"
STEP_FAILURE_THRESHOLD = "STEP_FAILURE_THRESHOLD"
REPLAN_REQUIRED = "REPLAN_REQUIRED"
STEP_SCOPE_UNPLANNED_FILE = "STEP_SCOPE_UNPLANNED_FILE"
STEP_SCOPE_EMPTY_DONE_STEP = "STEP_SCOPE_EMPTY_DONE_STEP"
STEP_SCOPE_OUTSIDE_TASK_SCOPE = "STEP_SCOPE_OUTSIDE_TASK_SCOPE"
VERIFICATION_REFS_INVALID = "VERIFICATION_REFS_INVALID"
MISSING_REF = "MISSING_REF"
EXPLANATION_SUMMARY_REQUIRED = "EXPLANATION_SUMMARY_REQUIRED"
PRECONDITION_UNCHECKED = "PRECONDITION_UNCHECKED"
SUBAGENT_SCOPE_VIOLATION = "SUBAGENT_SCOPE_VIOLATION"
RUST_FMT_FAILED = "RUST_FMT_FAILED"
RUST_CLIPPY_FAILED = "RUST_CLIPPY_FAILED"
RUST_TEST_FAILED = "RUST_TEST_FAILED"
ODIN_CHECK_FAILED = "ODIN_CHECK_FAILED"
ABI_WIDTH_MISMATCH = "ABI_WIDTH_MISMATCH"
ABI_LAYOUT_MISMATCH = "ABI_LAYOUT_MISMATCH"
PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
LAYOUT_PARITY_MISMATCH = "LAYOUT_PARITY_MISMATCH"
EVIDENCE_FILE_MISSING = "EVIDENCE_FILE_MISSING"

CODES = MappingProxyType(
    {
        OK: "Operation succeeded",
        SCHEMA_INVALID: "Artifact failed JSON schema validation",
        PLAN_STATUS_INVALID: "Illegal plan status transition",
        STEP_ORDER_INVALID: "Step ordering violated",
        STEP_FAILURE_THRESHOLD: "Step failure threshold exceeded",
        REPLAN_REQUIRED: "Execution halted pending replan",
        STEP_SCOPE_UNPLANNED_FILE: "Changed file outside step scope",
        STEP_SCOPE_EMPTY_DONE_STEP: "Completed step produced no file effects",
        STEP_SCOPE_OUTSIDE_TASK_SCOPE: "Step scope outside task scope",
        VERIFICATION_REFS_INVALID: "Invalid verification reference",
        MISSING_REF: "Verification reference points to missing entry",
        EXPLANATION_SUMMARY_REQUIRED: "Explanation summary required but missing",
        PRECONDITION_UNCHECKED: "Precondition lacks verification",
        SUBAGENT_SCOPE_VIOLATION: "Subagent modified files outside scope",
        RUST_FMT_FAILED: "cargo fmt failed",
        RUST_CLIPPY_FAILED: "cargo clippy failed",
        RUST_TEST_FAILED: "cargo test failed",
        ODIN_CHECK_FAILED: "odin check failed",
        ABI_WIDTH_MISMATCH: "ABI width mismatch",
        ABI_LAYOUT_MISMATCH: "ABI layout mismatch",
        PROTOCOL_MISMATCH: "Kernel and service protocol usage drifted from the ABI",
        LAYOUT_PARITY_MISMATCH: "Generated bindings do not preserve the heartbeat payload layout",
        EVIDENCE_FILE_MISSING: "Required evidence file missing",
    }
)
