from __future__ import annotations

import unittest

from harness.codes import STEP_ORDER_INVALID
from harness.validators_impl.plan_lifecycle import PlanLifecycleValidator

KOZO_NEGATIVE_COVERAGE = {
    "plan_lifecycle": {
        "out_of_order_step_ids": "test_fails_when_step_ids_are_out_of_order",
    }
}


class PlanLifecycleValidatorTests(unittest.TestCase):
    def test_fails_when_step_ids_are_out_of_order(self):
        bundle = {
            "todo": {
                "plan_status": "approved",
                "steps": [
                    {"id": 2, "status": "pending"},
                    {"id": 1, "status": "pending"},
                ],
            },
            "runtime": {"plan_status": "approved", "current_step_id": 1},
        }

        result = PlanLifecycleValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, STEP_ORDER_INVALID)


if __name__ == "__main__":
    unittest.main()
