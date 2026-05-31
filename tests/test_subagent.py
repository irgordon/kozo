from __future__ import annotations

import unittest

from harness.codes import SUBAGENT_SCOPE_VIOLATION
from harness.validators_impl.subagent import SubagentValidator

KOZO_NEGATIVE_COVERAGE = {
    "subagent": {
        "subagent_scope_declared": "test_fails_when_subagent_scope_is_declared",
    }
}


class SubagentValidatorTests(unittest.TestCase):
    def test_fails_when_subagent_scope_is_declared(self):
        bundle = {
            "todo": {"subagents": [{"name": "worker"}]},
            "runtime": {},
        }

        result = SubagentValidator().validate(bundle)

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SUBAGENT_SCOPE_VIOLATION)


if __name__ == "__main__":
    unittest.main()
