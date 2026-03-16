from types import MappingProxyType

ARTIFACT_VERSION = "1"
PASS = "pass"
FAIL = "fail"
SUMMARY_SUBSYSTEM_GENERIC = "generic"

PLAN_STATUSES = ("approved", "complete")
STEP_STATUSES = ("pending", "done")
STEP_KINDS = ("edit", "docs")
TASK_KINDS = ("non_trivial",)
APPROVAL_STATUSES = ("approved",)
CONTEXT_MODES = ("execute", "replan", "halted", "complete")
VERIFICATION_SECTIONS = (
    "tests_run",
    "logs",
    "diffs",
    "invariants",
    "expected_behavior",
    "actual_behavior",
)

SUBSYSTEMS = MappingProxyType(
    {
        SUMMARY_SUBSYSTEM_GENERIC: (),
        "schema": (),
        "lifecycle": (),
        "step_scope": (),
        "verification_refs": (),
        "explanation": (),
        "preconditions": (),
        "subagent": (),
        "rust": (),
        "odin": (),
        "abi": (),
        "protocol_alignment": (),
        "structural_integrity": (),
        "execution_foundation": (),
        "bridge_alignment": (),
        "execution_proof": (),
        "evidence": (),
    }
)

STATUSES = MappingProxyType(
    {
        PASS: "validator succeeded",
        FAIL: "validator failed",
    }
)

CHECKS = MappingProxyType(
    {
        "schema": "schema",
        "plan_lifecycle": "lifecycle",
        "step_scope": "step_scope",
        "verification_refs": "verification_refs",
        "explanation": "explanation",
        "preconditions": "preconditions",
        "subagent": "subagent",
        "rust": "rust",
        "odin": "odin",
        "abi": "abi",
        "protocol_alignment": "protocol_alignment",
        "layout_parity": "structural_integrity",
        "execution_foundation": "execution_foundation",
        "bridge_alignment": "bridge_alignment",
        "execution_proof": "execution_proof",
        "evidence": "evidence",
    }
)
