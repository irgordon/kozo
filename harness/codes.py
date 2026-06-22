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
ABI_MANIFEST_INVALID = "ABI_MANIFEST_INVALID"
ABI_SURFACE_REPORT_INVALID = "ABI_SURFACE_REPORT_INVALID"
GOVERNANCE_INDEX_REPORT_INVALID = "GOVERNANCE_INDEX_REPORT_INVALID"
SYSCALL_BOUNDARY_CONTRACT_INVALID = "SYSCALL_BOUNDARY_CONTRACT_INVALID"
SYSCALL_BOUNDARY_CONFORMANCE_INVALID = "SYSCALL_BOUNDARY_CONFORMANCE_INVALID"
SYSCALL_TABLE_CONTRACT_INVALID = "SYSCALL_TABLE_CONTRACT_INVALID"
SYSCALL_CLASS_CONTRACT_INVALID = "SYSCALL_CLASS_CONTRACT_INVALID"
SYSCALL_TABLE_CONFORMANCE_INVALID = "SYSCALL_TABLE_CONFORMANCE_INVALID"
SYSCALL_CATALOG_INVALID = "SYSCALL_CATALOG_INVALID"
SYSCALL_SURFACE_REPORT_INVALID = "SYSCALL_SURFACE_REPORT_INVALID"
PROTOCOL_MISMATCH = "PROTOCOL_MISMATCH"
LAYOUT_PARITY_MISMATCH = "LAYOUT_PARITY_MISMATCH"
EXECUTION_FOUNDATION_INVALID = "EXECUTION_FOUNDATION_INVALID"
BRIDGE_ALIGNMENT_INVALID = "BRIDGE_ALIGNMENT_INVALID"
RUNTIME_TRAP_PATH_INVALID = "RUNTIME_TRAP_PATH_INVALID"
RUNTIME_SMOKE_EVIDENCE_INVALID = "RUNTIME_SMOKE_EVIDENCE_INVALID"
RUNTIME_EVIDENCE_REVIEW_INVALID = "RUNTIME_EVIDENCE_REVIEW_INVALID"
RUNTIME_EVIDENCE_TAXONOMY_INVALID = "RUNTIME_EVIDENCE_TAXONOMY_INVALID"
RUNTIME_HALT_CONTRACT_INVALID = "RUNTIME_HALT_CONTRACT_INVALID"
RUNTIME_PROGRESSION_CONTRACT_INVALID = "RUNTIME_PROGRESSION_CONTRACT_INVALID"
RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID = "RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID"
RUNTIME_PROGRESSION_STAGES_INVALID = "RUNTIME_PROGRESSION_STAGES_INVALID"
STACK_INITIALIZATION_EVIDENCE_CONTRACT_INVALID = "STACK_INITIALIZATION_EVIDENCE_CONTRACT_INVALID"
BOOT_BLOCKER_REPORT_INVALID = "BOOT_BLOCKER_REPORT_INVALID"
BOOT_PROTOCOL_DECISION_INVALID = "BOOT_PROTOCOL_DECISION_INVALID"
BOOT_IMAGE_SKELETON_INVALID = "BOOT_IMAGE_SKELETON_INVALID"
BOOT_IMAGE_PACKAGING_INVALID = "BOOT_IMAGE_PACKAGING_INVALID"
BOOT_TOOLING_INVALID = "BOOT_TOOLING_INVALID"
KERNEL_LOADABILITY_INVALID = "KERNEL_LOADABILITY_INVALID"
HOST_DEPENDENCY_PORTABILITY_INVALID = "HOST_DEPENDENCY_PORTABILITY_INVALID"
QEMU_SMOKE_EVIDENCE_INVALID = "QEMU_SMOKE_EVIDENCE_INVALID"
RETURN_PATH_PROOF_INVALID = "RETURN_PATH_PROOF_INVALID"
EXECUTION_PROOF_INVALID = "EXECUTION_PROOF_INVALID"
VALIDATOR_COVERAGE_INVALID = "VALIDATOR_COVERAGE_INVALID"
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
        ABI_MANIFEST_INVALID: "ABI manifest is missing, invalid, or inconsistent with the canonical ABI",
        ABI_SURFACE_REPORT_INVALID: "Generated ABI surface report is missing or stale",
        GOVERNANCE_INDEX_REPORT_INVALID: "Generated governance index report is missing or stale",
        SYSCALL_BOUNDARY_CONTRACT_INVALID: "Syscall boundary contract is missing, invalid, or inconsistent with the proven trap path",
        SYSCALL_BOUNDARY_CONFORMANCE_INVALID: "Live sources do not conform to the syscall boundary contract",
        SYSCALL_TABLE_CONTRACT_INVALID: "Syscall table contract is missing, invalid, or inconsistent with the live dispatcher",
        SYSCALL_CLASS_CONTRACT_INVALID: "Syscall class contract is missing, invalid, or inconsistent with the syscall table contract",
        SYSCALL_TABLE_CONFORMANCE_INVALID: "Live dispatcher source does not conform to the syscall table contract",
        SYSCALL_CATALOG_INVALID: "Syscall catalog is missing, invalid, or inconsistent with governed syscall contracts",
        SYSCALL_SURFACE_REPORT_INVALID: "Generated syscall surface report is missing or stale",
        PROTOCOL_MISMATCH: "Kernel and service protocol usage drifted from the ABI",
        LAYOUT_PARITY_MISMATCH: "Generated bindings do not preserve the heartbeat payload layout",
        EXECUTION_FOUNDATION_INVALID: "Kernel boot and trap entry symbols are misaligned with the execution foundation contract",
        BRIDGE_ALIGNMENT_INVALID: "Assembly ingress registers do not align with the exported Odin trap dispatcher signature",
        RUNTIME_TRAP_PATH_INVALID: "Rust does not cross the assembly syscall bridge as required by the runtime trap contract",
        RUNTIME_SMOKE_EVIDENCE_INVALID: "Runtime smoke evidence is missing, malformed, or inconsistent with release evidence policy",
        RUNTIME_EVIDENCE_REVIEW_INVALID: "Runtime evidence review policy is missing, incomplete, or overclaim-prone",
        RUNTIME_EVIDENCE_TAXONOMY_INVALID: "Runtime evidence taxonomy is missing, malformed, or inconsistent with governed smoke vocabulary",
        RUNTIME_HALT_CONTRACT_INVALID: "Runtime halt contract is missing, malformed, or inconsistent with the post-smoke terminal path",
        RUNTIME_PROGRESSION_CONTRACT_INVALID: "Runtime progression contract is missing, malformed, or inconsistent with halt-to-runtime transition governance",
        RUNTIME_PROGRESSION_ENTRY_CONTRACT_INVALID: "Runtime progression entry contract is missing, malformed, or inconsistent with future entry governance",
        RUNTIME_PROGRESSION_STAGES_INVALID: "Runtime progression stages contract is missing, malformed, or inconsistent with canonical progression ordering",
        STACK_INITIALIZATION_EVIDENCE_CONTRACT_INVALID: "Stack initialization evidence contract is missing, malformed, or inconsistent with future stack proof governance",
        BOOT_BLOCKER_REPORT_INVALID: "Boot blocker report is missing, malformed, or inconsistent with boot baseline policy",
        BOOT_PROTOCOL_DECISION_INVALID: "Boot protocol decision is missing, incomplete, or inconsistent with boot blocker policy",
        BOOT_IMAGE_SKELETON_INVALID: "Boot image skeleton is missing, incomplete, or inconsistent with boot blocker state",
        BOOT_IMAGE_PACKAGING_INVALID: "Boot image packaging metadata is missing, malformed, or inconsistent with boot blocker state",
        BOOT_TOOLING_INVALID: "Boot tooling policy is missing, incomplete, or inconsistent with boot blocker state",
        KERNEL_LOADABILITY_INVALID: "Kernel ELF loadability evidence is missing, malformed, or inconsistent with boot blocker state",
        HOST_DEPENDENCY_PORTABILITY_INVALID: "Host dependency portability policy is missing, malformed, or relies on local host state",
        QEMU_SMOKE_EVIDENCE_INVALID: "QEMU smoke evidence is missing, malformed, or inconsistent with boot evidence policy",
        RETURN_PATH_PROOF_INVALID: "Rust does not prove that post-call payload mutations are observed after the trap bridge returns",
        EXECUTION_PROOF_INVALID: "Syscall execution behavior proof is missing or misordered in source",
        VALIDATOR_COVERAGE_INVALID: "Registered validators do not have focused negative-path test coverage",
        EVIDENCE_FILE_MISSING: "Required evidence file missing",
    }
)
