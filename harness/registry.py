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
        "abi_manifest": (),
        "abi_surface_report": (),
        "syscall_boundary_contract": (),
        "syscall_boundary_conformance": (),
        "syscall_table_contract": (),
        "syscall_class_contract": (),
        "syscall_table_conformance": (),
        "syscall_catalog": (),
        "syscall_surface_report": (),
        "governance_index_report": (),
        "protocol_contract_alignment": (),
        "structural_integrity": (),
        "execution_foundation": (),
        "bridge_alignment": (),
        "runtime_trap_path": (),
        "runtime_smoke_evidence": (),
        "runtime_evidence_review": (),
        "runtime_evidence_taxonomy": (),
        "runtime_halt_contract": (),
        "runtime_progression_contract": (),
        "runtime_progression_entry_contract": (),
        "boot_blocker_report": (),
        "boot_protocol_decision": (),
        "boot_image_skeleton": (),
        "boot_image_packaging": (),
        "boot_tooling": (),
        "kernel_loadability": (),
        "host_dependency_portability": (),
        "qemu_smoke_evidence": (),
        "return_path_proof": (),
        "execution_proof": (),
        "validator_coverage": (),
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
        "abi_manifest": "abi_manifest",
        "abi_surface_report": "abi_surface_report",
        "syscall_boundary_contract": "syscall_boundary_contract",
        "syscall_boundary_conformance": "syscall_boundary_conformance",
        "syscall_table_contract": "syscall_table_contract",
        "syscall_class_contract": "syscall_class_contract",
        "syscall_table_conformance": "syscall_table_conformance",
        "syscall_catalog": "syscall_catalog",
        "syscall_surface_report": "syscall_surface_report",
        "governance_index_report": "governance_index_report",
        "protocol_contract_alignment": "protocol_contract_alignment",
        "layout_parity": "structural_integrity",
        "execution_foundation": "execution_foundation",
        "bridge_alignment": "bridge_alignment",
        "runtime_trap_path": "runtime_trap_path",
        "runtime_smoke_evidence": "runtime_smoke_evidence",
        "runtime_evidence_review": "runtime_evidence_review",
        "runtime_evidence_taxonomy": "runtime_evidence_taxonomy",
        "runtime_halt_contract": "runtime_halt_contract",
        "runtime_progression_contract": "runtime_progression_contract",
        "runtime_progression_entry_contract": "runtime_progression_entry_contract",
        "boot_blocker_report": "boot_blocker_report",
        "boot_protocol_decision": "boot_protocol_decision",
        "boot_image_skeleton": "boot_image_skeleton",
        "boot_image_packaging": "boot_image_packaging",
        "boot_tooling": "boot_tooling",
        "kernel_loadability": "kernel_loadability",
        "host_dependency_portability": "host_dependency_portability",
        "qemu_smoke_evidence": "qemu_smoke_evidence",
        "return_path_proof": "return_path_proof",
        "execution_proof": "execution_proof",
        "validator_coverage": "validator_coverage",
        "evidence": "evidence",
    }
)
