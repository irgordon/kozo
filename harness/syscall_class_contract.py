from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "syscall_class_contract.v0.json"


@dataclass(frozen=True)
class SyscallClass:
    name: str
    payload_argument: str
    payload_layout_required: bool
    request_required: bool
    response_required: bool
    mutates_payload: str
    return_status_required: bool
    invalid_behavior_required: tuple[str, ...]
    valid_examples: tuple[str, ...]


@dataclass(frozen=True)
class SyscallClassContract:
    version: int
    classes: tuple[SyscallClass, ...]


def load_syscall_class_contract(path: Path = CONTRACT_PATH) -> SyscallClassContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_syscall_class_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("syscall_class_contract", data)


def parse_syscall_class_contract(data: dict[str, Any]) -> SyscallClassContract:
    return SyscallClassContract(
        version=data["version"],
        classes=_classes(data),
    )


def _classes(data: dict[str, Any]) -> tuple[SyscallClass, ...]:
    return tuple(
        _syscall_class(name, class_data)
        for name, class_data in data["classes"].items()
        if isinstance(name, str) and isinstance(class_data, dict)
    )


def _syscall_class(name: str, data: dict[str, Any]) -> SyscallClass:
    return SyscallClass(
        name=name,
        payload_argument=data["payload_argument"],
        payload_layout_required=data["payload_layout_required"],
        request_required=data["request_required"],
        response_required=data["response_required"],
        mutates_payload=data["mutates_payload"],
        return_status_required=data["return_status_required"],
        invalid_behavior_required=tuple(data.get("invalid_behavior_required", ())),
        valid_examples=tuple(data["valid_examples"]),
    )
