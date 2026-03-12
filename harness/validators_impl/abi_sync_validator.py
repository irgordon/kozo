from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from harness.codes import ABI_LAYOUT_MISMATCH, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_GENERATOR_PATH = _ROOT / "scripts" / "gen_abi.py"


def _load_generator_module():
    spec = importlib.util.spec_from_file_location("kozo_gen_abi", _GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ABI generator from {_GENERATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class AbiValidator(BaseValidator):
    name = "abi"
    subsystem = "abi"

    def validate(self, artifact_bundle):
        generator = _load_generator_module()
        abi_spec = generator.load_abi_spec()
        for path, expected in generator.render_targets(abi_spec).items():
            if not path.is_file():
                return ValidationResult.fail(
                    code=ABI_LAYOUT_MISMATCH,
                    detail=f"Generated ABI binding is missing: {path.relative_to(_ROOT)}",
                    action="Run python3 scripts/gen_abi.py to regenerate checked-in bindings",
                )
            actual = path.read_text()
            if actual != expected:
                return ValidationResult.fail(
                    code=ABI_LAYOUT_MISMATCH,
                    detail=f"Generated ABI binding drifted from the normative header: {path.relative_to(_ROOT)}",
                    action="Edit contracts/kozo_abi.h or scripts/gen_abi.py, then regenerate bindings",
                )
        return ValidationResult.pass_(code=OK, detail="Checked-in ABI bindings match the normative header")
