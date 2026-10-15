from __future__ import annotations

import json
from pathlib import Path

from harness.validators_impl.schema import validate_named_document

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / 'contracts/fixed_user_request_boundary_contract.v1.json'
RESPONSE_QWORDS = 12
U64_MAX = (1 << 64) - 1


def load_contract(path=CONTRACT_PATH):
    contract = json.loads(path.read_text())
    validate_contract(contract)
    return contract


def validate_contract(contract):
    validate_named_document('fixed_user_request_boundary_contract_v1', contract)


def response_digest(qwords):
    if len(qwords) != RESPONSE_QWORDS:
        raise ValueError('Response digest requires exactly twelve qwords')
    digest = 0
    for value in qwords:
        if type(value) is not int or not 0 <= value <= U64_MAX:
            raise ValueError('Response digest requires u64 values')
        digest ^= value
    return digest
