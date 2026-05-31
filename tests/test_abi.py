from __future__ import annotations

import unittest

from harness.codes import ABI_LAYOUT_MISMATCH
from harness.validators_impl import abi_sync_validator
from harness.validators_impl.abi import AbiValidator


class AbiValidatorTests(unittest.TestCase):
    def test_fails_when_generated_binding_is_missing(self):
        missing_path = abi_sync_validator._ROOT / "bindings" / "__missing_for_test.rs"

        class FakeGenerator:
            @staticmethod
            def load_abi_spec():
                return {}

            @staticmethod
            def render_targets(_abi_spec):
                return {missing_path: "expected"}

        original_loader = abi_sync_validator._load_generator_module
        abi_sync_validator._load_generator_module = lambda: FakeGenerator
        try:
            result = AbiValidator().validate({})
        finally:
            abi_sync_validator._load_generator_module = original_loader

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, ABI_LAYOUT_MISMATCH)


if __name__ == "__main__":
    unittest.main()
