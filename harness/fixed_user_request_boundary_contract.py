from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from harness.abi_manifest import ROOT
from harness.validators_impl.schema import validate_named_document

CONTRACT_PATH = ROOT / "contracts" / "fixed_user_request_boundary_contract.v0.json"


@dataclass(frozen=True)
class FixedUserRequestBoundaryContract:
    version: int
    architecture: str
    source_files: dict[str, str]
    execution_point: dict[str, Any]
    request: dict[str, Any]
    response: dict[str, Any]
    kernel_shadows: dict[str, Any]
    fixed_service: dict[str, Any]
    copy_boundary: dict[str, Any]
    page_permissions: dict[str, Any]
    buffer_clearing: dict[str, Any]
    marker_order: tuple[str, ...]
    marker_ownership: dict[str, str]
    failure_statuses: dict[str, int]
    halt_behavior: dict[str, Any]
    claim_boundary: dict[str, tuple[str, ...]]
    non_goals: tuple[str, ...]


def load_fixed_user_request_boundary_contract(
    path: Path = CONTRACT_PATH,
) -> FixedUserRequestBoundaryContract:
    data = json.loads(path.read_text())
    validate_named_document("fixed_user_request_boundary_contract", data)
    return _parse_contract(data)


def response_token(payload: int, mask: int) -> int:
    _require_u64(payload, "payload")
    _require_u64(mask, "mask")
    return payload ^ mask


def fixed_spans_are_valid(contract: FixedUserRequestBoundaryContract) -> bool:
    request_start = _hex_int(contract.request["virtual_address"])
    response_start = _hex_int(contract.response["virtual_address"])
    request_end = _checked_end(request_start, contract.request["size_bytes"])
    response_end = _checked_end(response_start, contract.response["size_bytes"])
    page_start = _hex_int(contract.page_permissions["page_start"])
    page_end = _hex_int(contract.page_permissions["page_end"])
    if request_end is None or response_end is None:
        return False
    return (
        page_start <= request_start < request_end <= page_end
        and page_start <= response_start < response_end <= page_end
        and request_end <= response_start
    )


def _parse_contract(data: dict[str, Any]) -> FixedUserRequestBoundaryContract:
    return FixedUserRequestBoundaryContract(
        version=data["version"],
        architecture=data["architecture"],
        source_files=dict(data["source_files"]),
        execution_point=dict(data["execution_point"]),
        request=dict(data["request"]),
        response=dict(data["response"]),
        kernel_shadows=dict(data["kernel_shadows"]),
        fixed_service=dict(data["fixed_service"]),
        copy_boundary=dict(data["copy_boundary"]),
        page_permissions=dict(data["page_permissions"]),
        buffer_clearing=dict(data["buffer_clearing"]),
        marker_order=tuple(data["marker_order"]),
        marker_ownership=dict(data["marker_ownership"]),
        failure_statuses=dict(data["failure_statuses"]),
        halt_behavior=dict(data["halt_behavior"]),
        claim_boundary={
            key: tuple(values)
            for key, values in data["claim_boundary"].items()
        },
        non_goals=tuple(data["non_goals"]),
    )


def _hex_int(value: Any) -> int:
    if not isinstance(value, str):
        raise ValueError("address and mask values must be hexadecimal strings")
    return int(value, 16)


def _checked_end(start: int, size: Any) -> int | None:
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        return None
    end = start + size
    return end if end <= 0xFFFFFFFFFFFFFFFF else None


def _require_u64(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"{name} must be an unsigned 64-bit integer")
