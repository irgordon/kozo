import copy
import unittest

from scripts.compare_portability_release_inputs import (
    CrossHostIdentityError,
    compare_release_input_evidence,
)


class ReleaseInputPortabilityTests(unittest.TestCase):
    def test_identical_records_pass(self):
        report = compare_release_input_evidence(sample_host_evidence())

        self.assertEqual(report["result"], "PASS")
        self.assertEqual(report["comparison_dimensions"], ["path", "size", "sha256"])
        self.assertEqual(len(report["files"]), 3)

    def test_different_size_fails(self):
        evidence = sample_host_evidence()
        evidence["windows"]["release_inputs"]["files"][0]["size"] += 1

        with self.assertRaises(CrossHostIdentityError):
            compare_release_input_evidence(evidence)

    def test_different_hash_fails(self):
        evidence = sample_host_evidence()
        evidence["windows"]["release_inputs"]["files"][0]["sha256"] = "f" * 64

        with self.assertRaises(CrossHostIdentityError):
            compare_release_input_evidence(evidence)

    def test_missing_governed_entry_fails(self):
        evidence = sample_host_evidence()
        evidence["windows"]["release_inputs"]["files"].pop()

        with self.assertRaises(CrossHostIdentityError):
            compare_release_input_evidence(evidence)

    def test_duplicate_governed_entry_fails(self):
        evidence = sample_host_evidence()
        duplicate = copy.deepcopy(evidence["windows"]["release_inputs"]["files"][0])
        evidence["windows"]["release_inputs"]["files"].append(duplicate)

        with self.assertRaises(CrossHostIdentityError):
            compare_release_input_evidence(evidence)

    def test_different_host_order_passes(self):
        evidence = sample_host_evidence()
        evidence["windows"]["release_inputs"]["files"].reverse()

        report = compare_release_input_evidence(evidence)

        self.assertEqual(report["result"], "PASS")

    def test_different_commit_fails(self):
        evidence = sample_host_evidence()
        evidence["windows"]["commit"] = "other"

        with self.assertRaises(CrossHostIdentityError):
            compare_release_input_evidence(evidence)

    def test_report_has_no_host_specific_expected_values(self):
        report = compare_release_input_evidence(sample_host_evidence())

        self.assertNotIn("expected_by_host", report)
        self.assertEqual(report["hosts"], ["linux", "macos", "windows"])


def sample_host_evidence() -> dict[str, dict]:
    files = [
        {"path": "LICENSE", "size": 335, "sha256": "a" * 64},
        {"path": "LICENSE-APACHE", "size": 567, "sha256": "b" * 64},
        {"path": "LICENSE-MIT", "size": 1066, "sha256": "c" * 64},
    ]
    return {
        host: {
            "commit": "accepted",
            "build_contract": "PASS",
            "release_inputs": {
                "authority": "git_blob",
                "result": "PASS",
                "files": [
                    record
                    | {
                        "staged_size": record["size"],
                        "staged_sha256": record["sha256"],
                    }
                    for record in copy.deepcopy(files)
                ],
            },
        }
        for host in ("linux", "macos", "windows")
    }


if __name__ == "__main__":
    unittest.main()
