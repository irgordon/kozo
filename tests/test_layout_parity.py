from __future__ import annotations

import unittest

from harness.codes import LAYOUT_PARITY_MISMATCH
from harness.validators_impl import layout_parity
from harness.validators_impl.layout_parity import LayoutParityValidator


class LayoutParityValidatorTests(unittest.TestCase):
    def test_fails_when_normative_layout_is_wrong(self):
        class FakeGenerator:
            @staticmethod
            def load_abi_spec():
                return {}

            @staticmethod
            def get_struct(_abi_spec, _name):
                return {}

            @staticmethod
            def calculate_struct_layout(_heartbeat_struct):
                return {"size": 16, "alignment": 8, "offsets": {}}

        original_loader = layout_parity._load_generator_module
        layout_parity._load_generator_module = lambda: FakeGenerator
        try:
            result = LayoutParityValidator().validate({})
        finally:
            layout_parity._load_generator_module = original_loader

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, LAYOUT_PARITY_MISMATCH)


if __name__ == "__main__":
    unittest.main()
