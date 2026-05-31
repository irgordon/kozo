from __future__ import annotations

import unittest

from harness.codes import SCHEMA_INVALID
from harness.validators_impl.schema import SchemaValidator

KOZO_NEGATIVE_COVERAGE = {
    "schema": {
        "missing_required_schema_fields": "test_fails_when_required_schema_fields_are_missing",
    }
}


class SchemaValidatorTests(unittest.TestCase):
    def test_fails_when_required_schema_fields_are_missing(self):
        result = SchemaValidator().validate({"todo": {}, "runtime": {}})

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, SCHEMA_INVALID)


if __name__ == "__main__":
    unittest.main()
