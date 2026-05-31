from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.validators_impl.schema import validate_named_document

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "contracts" / "kozo_abi_manifest.json"


@dataclass(frozen=True)
class GeneratedBindingPaths:
    rust: str
    odin: str


@dataclass(frozen=True)
class ManifestConstants:
    status: dict[str, int]
    syscalls: dict[str, int]


@dataclass(frozen=True)
class ManifestLayoutField:
    name: str
    width: int
    offset: int


@dataclass(frozen=True)
class ManifestLayout:
    c_name: str
    rust_name: str
    odin_name: str
    size: int
    alignment: int
    fields: tuple[ManifestLayoutField, ...]


@dataclass(frozen=True)
class HeartbeatSentinels:
    sequence: str | int
    timestamp: str | int
    status_bits: str


@dataclass(frozen=True)
class ManifestHeartbeat:
    request: HeartbeatSentinels
    response: HeartbeatSentinels


@dataclass(frozen=True)
class AbiManifest:
    version: int
    canonical_header: str
    generated_bindings: GeneratedBindingPaths
    constants: ManifestConstants
    heartbeat_payload: ManifestLayout
    heartbeat: ManifestHeartbeat


def load_abi_manifest(path: Path = MANIFEST_PATH) -> AbiManifest:
    data = load_manifest_json(path)
    validate_manifest_shape(data)
    return parse_abi_manifest(data)


def load_manifest_json(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate_manifest_shape(data: dict[str, Any]) -> None:
    validate_named_document("kozo_abi_manifest", data)


def parse_abi_manifest(data: dict[str, Any]) -> AbiManifest:
    return AbiManifest(
        version=data["version"],
        canonical_header=data["canonical_header"],
        generated_bindings=_generated_binding_paths(data),
        constants=_manifest_constants(data),
        heartbeat_payload=_manifest_layout(data),
        heartbeat=_manifest_heartbeat(data),
    )


def manifest_repo_path(manifest_path: str) -> Path:
    path = Path(manifest_path)
    if path.is_absolute():
        return path
    return ROOT / path


def _generated_binding_paths(data: dict[str, Any]) -> GeneratedBindingPaths:
    bindings = data["generated_bindings"]
    return GeneratedBindingPaths(bindings["rust"], bindings["odin"])


def _manifest_constants(data: dict[str, Any]) -> ManifestConstants:
    constants = data["constants"]
    return ManifestConstants(
        _integer_map(constants["status"]),
        _integer_map(constants["syscalls"]),
    )


def _manifest_layout(data: dict[str, Any]) -> ManifestLayout:
    layout = data["layouts"]["heartbeat_payload"]
    return ManifestLayout(
        c_name=layout["c_name"],
        rust_name=layout["rust_name"],
        odin_name=layout["odin_name"],
        size=layout["size"],
        alignment=layout["alignment"],
        fields=tuple(
            ManifestLayoutField(field["name"], field["width"], field["offset"])
            for field in layout["fields"]
        ),
    )


def _manifest_heartbeat(data: dict[str, Any]) -> ManifestHeartbeat:
    heartbeat = data["heartbeat"]
    return ManifestHeartbeat(
        request=_heartbeat_sentinels(heartbeat["request"]),
        response=_heartbeat_sentinels(heartbeat["response"]),
    )


def _heartbeat_sentinels(data: dict[str, Any]) -> HeartbeatSentinels:
    return HeartbeatSentinels(
        sequence=data["sequence"],
        timestamp=data["timestamp"],
        status_bits=data["status_bits"],
    )


def _integer_map(data: dict[str, Any]) -> dict[str, int]:
    return {
        name: value
        for name, value in data.items()
        if isinstance(name, str) and isinstance(value, int) and not isinstance(value, bool)
    }
