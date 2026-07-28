from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts import kernel_elf_report

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "elf"
LLVM_FIXTURE = FIXTURE_ROOT / "llvm_ring3_response_consumer.txt"
GNU_FIXTURE = FIXTURE_ROOT / "gnu_ring3_response_consumer.txt"
CONSUMER_START = 0xFFFFFFFF80207090
CONSUMER_END = 0xFFFFFFFF80207226
CONSUMER_SYMBOLS = {
    "user_response_consumer_start": CONSUMER_START,
    "user_response_consumer_end": CONSUMER_END,
}


class KernelElfReportTests(unittest.TestCase):
    def test_llvm_fixture_proves_complete_consumer(self):
        evidence = self.fixture_evidence(LLVM_FIXTURE)
        self.assert_complete_consumer(evidence)

    def test_gnu_fixture_proves_complete_consumer(self):
        evidence = self.fixture_evidence(GNU_FIXTURE)
        self.assert_complete_consumer(evidence)

    def test_gnu_and_llvm_fixtures_produce_equal_evidence(self):
        llvm = self.fixture_evidence(LLVM_FIXTURE)
        gnu = self.fixture_evidence(GNU_FIXTURE)
        self.assertEqual(llvm["ring3_response_compare_count"], 18)
        self.assertEqual(
            llvm["ring3_response_compare_count"],
            gnu["ring3_response_compare_count"],
        )
        self.assertEqual(
            llvm["ring3_response_observed_offsets"],
            gnu["ring3_response_observed_offsets"],
        )
        self.assertEqual(
            llvm["ring3_response_consumer_instruction_count"],
            gnu["ring3_response_consumer_instruction_count"],
        )

    def test_missing_consumer_symbol_fails(self):
        symbols = {"user_response_consumer_end": CONSUMER_END}
        evidence = self.fixture_evidence(GNU_FIXTURE, symbols)
        self.assertFalse(evidence["ring3_response_consumer_symbol_found"])
        self.assertEqual(evidence["ring3_response_consumer_instruction_count"], 0)
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_missing_consumer_end_fails(self):
        symbols = {"user_response_consumer_start": CONSUMER_START}
        evidence = self.fixture_evidence(GNU_FIXTURE, symbols)
        self.assertFalse(evidence["ring3_response_consumer_symbol_found"])
        self.assertEqual(evidence["ring3_response_consumer_instruction_count"], 0)
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_empty_consumer_body_fails(self):
        symbols = {
            "user_response_consumer_start": CONSUMER_END,
            "user_response_consumer_end": CONSUMER_END + 1,
        }
        evidence = self.fixture_evidence(GNU_FIXTURE, symbols)
        self.assertTrue(evidence["ring3_response_consumer_symbol_found"])
        self.assertEqual(evidence["ring3_response_consumer_instruction_count"], 0)
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_too_few_comparisons_fail(self):
        text = GNU_FIXTURE.read_text()
        addresses = (
            "ffffffff802070a0:",
            "ffffffff802070b6:",
            "ffffffff802070cb:",
            "ffffffff802070d4:",
            "ffffffff802070e3:",
        )
        evidence = self.text_evidence(self.remove_lines(text, addresses))
        self.assertEqual(evidence["ring3_response_compare_count"], 13)
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_comparisons_outside_consumer_do_not_count(self):
        text = GNU_FIXTURE.read_text()
        text = (
            "ffffffff80207080:\t48 83 f8 00\tcmp $0x0,%rax\n"
            + text
            + "\nffffffff80207230:\t48 83 f8 00\tcmp $0x0,%rax\n"
        )
        evidence = self.text_evidence(text)
        self.assertEqual(evidence["ring3_response_compare_count"], 18)

    def test_success_stores_before_comparisons_fail(self):
        text = GNU_FIXTURE.read_text().replace(
            "ffffffff802071c0:\tc7 06 01 00 00 00",
            "ffffffff802070df:\tc7 06 01 00 00 00",
            1,
        )
        evidence = self.text_evidence(text)
        self.assertFalse(
            evidence["ring3_response_comparisons_before_success_store"]
        )
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_second_interrupt_before_comparisons_fails(self):
        text = GNU_FIXTURE.read_text().replace(
            "ffffffff80207222:\tcd 81",
            "ffffffff802070e0:\tcd 81",
            1,
        )
        evidence = self.text_evidence(text)
        self.assertFalse(evidence["ring3_response_success_store_before_interrupt"])
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_failure_sink_interrupt_does_not_satisfy_success_path(self):
        text = self.remove_lines(GNU_FIXTURE.read_text(), ("ffffffff80207222:",))
        text += "\nffffffff80207230:\tcd 81\tint $0x81\n"
        evidence = self.text_evidence(text)
        self.assertFalse(evidence["ring3_response_second_interrupt_present"])
        self.assertFalse(evidence["ring3_response_order_valid"])

    def test_consumer_evidence_serializes_as_json(self):
        evidence = self.fixture_evidence(GNU_FIXTURE)
        serialized = json.loads(json.dumps(evidence))
        self.assertEqual(serialized["ring3_response_compare_count"], 18)
        self.assertTrue(serialized["ring3_response_order_valid"])

    def fixture_evidence(self, fixture, symbols=CONSUMER_SYMBOLS):
        return self.text_evidence(fixture.read_text(), symbols)

    def text_evidence(self, text, symbols=CONSUMER_SYMBOLS):
        return kernel_elf_report.build_ring3_response_consumer_evidence(
            text,
            symbols,
            kernel_elf_report.runtime_status_response_offsets(),
        )

    def remove_lines(self, text, prefixes):
        return "\n".join(
            line
            for line in text.splitlines()
            if not line.startswith(prefixes)
        )

    def assert_complete_consumer(self, evidence):
        expected_offsets = [
            "0x00",
            "0x04",
            "0x08",
            "0x0c",
            "0x10",
            "0x18",
            "0x1c",
            "0x20",
            "0x28",
            "0x30",
            "0x38",
            "0x40",
            "0x48",
            "0x50",
        ]
        self.assertTrue(evidence["ring3_response_consumer_symbol_found"])
        self.assertEqual(evidence["ring3_response_consumer_instruction_count"], 89)
        self.assertEqual(evidence["ring3_response_compare_count"], 18)
        self.assertEqual(evidence["ring3_response_expected_offsets"], expected_offsets)
        self.assertEqual(evidence["ring3_response_observed_offsets"], expected_offsets)
        self.assertEqual(evidence["ring3_response_missing_offsets"], [])
        self.assertEqual(evidence["ring3_response_success_store_count"], 8)
        self.assertTrue(evidence["ring3_response_second_interrupt_present"])
        self.assertTrue(evidence["ring3_response_order_valid"])


if __name__ == "__main__":
    unittest.main()
