from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "runtime_halt_contract.v0.json"


@dataclass(frozen=True)
class HaltSource:
    path: str
    entry_symbol: str


@dataclass(frozen=True)
class FinalSmokeMarker:
    symbol: str
    text: str
    write_macro: str


@dataclass(frozen=True)
class TerminalBehavior:
    kind: str
    label: str
    disable_interrupts: bool
    instructions: tuple[str, ...]
    fallthrough_forbidden: bool


@dataclass(frozen=True)
class RuntimeHaltContract:
    version: int
    architecture: str
    source: HaltSource
    final_smoke_marker: FinalSmokeMarker
    terminal_behavior: TerminalBehavior
    non_goals: tuple[str, ...]


def load_runtime_halt_contract(path: Path = CONTRACT_PATH) -> RuntimeHaltContract:
    data = load_contract_json(path)
    validate_contract_shape(data)
    return parse_runtime_halt_contract(data)


def load_contract_json(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_contract_shape(data: dict[str, Any]) -> None:
    validate_named_document("runtime_halt_contract", data)


def parse_runtime_halt_contract(data: dict[str, Any]) -> RuntimeHaltContract:
    return RuntimeHaltContract(
        data["version"],
        data["architecture"],
        _source(data),
        _final_smoke_marker(data),
        _terminal_behavior(data),
        tuple(data["non_goals"]),
    )


def contract_repo_path(contract_path: str) -> Path:
    path = Path(contract_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _source(data: dict[str, Any]) -> HaltSource:
    source = data["source"]
    return HaltSource(source["path"], source["entry_symbol"])


def _final_smoke_marker(data: dict[str, Any]) -> FinalSmokeMarker:
    marker = data["final_smoke_marker"]
    return FinalSmokeMarker(marker["symbol"], marker["text"], marker["write_macro"])


def _terminal_behavior(data: dict[str, Any]) -> TerminalBehavior:
    behavior = data["terminal_behavior"]
    return TerminalBehavior(
        behavior["kind"],
        behavior["label"],
        behavior["disable_interrupts"],
        tuple(behavior["instructions"]),
        behavior["fallthrough_forbidden"],
    )
