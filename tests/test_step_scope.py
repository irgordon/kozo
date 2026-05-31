from __future__ import annotations

import unittest

from harness.codes import STEP_SCOPE_OUTSIDE_TASK_SCOPE
from harness.validators_impl.step_scope import StepScopeValidator

KOZO_NEGATIVE_COVERAGE = {
    "step_scope": {
        "outside_task_scope": "test_fails_when_changed_file_is_outside_task_scope",
    }
}


class StepScopeValidatorTests(unittest.TestCase):
    def test_fails_when_changed_file_is_outside_task_scope(self):
        bundle = {
            "todo": {
                "file_scope": ["harness/"],
                "steps": [
                    {"id": 1, "status": "pending", "files_expected": ["harness/validators.py"]},
                ],
            },
            "runtime": {"plan_status": "approved", "current_step_id": 1},
            "changed_files": ["kernel/main.odin"],
        }

        result = StepScopeValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, STEP_SCOPE_OUTSIDE_TASK_SCOPE)


if __name__ == "__main__":
    unittest.main()
