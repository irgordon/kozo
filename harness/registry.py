from types import MappingProxyType

ARTIFACT_VERSION = "1"

SUBSYSTEMS = MappingProxyType({
    "generic": (),
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
    "evidence": (),
})

STATUSES = MappingProxyType({
    "pass": "validator succeeded",
    "fail": "validator failed",
})

CHECKS = MappingProxyType({
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
    "evidence": "evidence",
})