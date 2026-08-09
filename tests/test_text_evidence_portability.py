from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
import unittest

from harness.text_evidence import (
    canonical_text_bytes,
    raw_artifact_size,
    write_canonical_text,
)
from scripts.host_portability_contract import sha256


class TextEvidencePortabilityTests(unittest.TestCase):
    def test_lf_crlf_and_cr_have_same_canonical_bytes(self):
        expected = b"first\nsecond\n"

        for text in ("first\nsecond\n", "first\r\nsecond\r\n", "first\rsecond\r"):
            with self.subTest(representation=repr(text)):
                self.assertEqual(canonical_text_bytes(text), expected)

    def test_empty_text_has_no_bytes(self):
        self.assertEqual(canonical_text_bytes(""), b"")

    def test_single_line_text_is_preserved(self):
        self.assertEqual(canonical_text_bytes("KOZO_RUNTIME_RETURN_OK"), b"KOZO_RUNTIME_RETURN_OK")

    def test_multiline_text_preserves_line_structure(self):
        self.assertEqual(canonical_text_bytes("one\ntwo\nthree"), b"one\ntwo\nthree")

    def test_utf8_text_uses_utf8_bytes(self):
        self.assertEqual(canonical_text_bytes("KOZO caf\N{LATIN SMALL LETTER E WITH ACUTE}\n"), "KOZO caf\N{LATIN SMALL LETTER E WITH ACUTE}\n".encode("utf-8"))

    def test_canonical_writer_uses_lf_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "evidence.txt"

            write_canonical_text(path, "first\r\nsecond\r")

            self.assertEqual(path.read_bytes(), b"first\nsecond\n")
            self.assertEqual(raw_artifact_size(path), len(b"first\nsecond\n"))

    def test_raw_binary_artifact_is_not_normalized(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "artifact.bin"
            binary = b"\x00\r\n\xff\r\x7f"
            path.write_bytes(binary)

            self.assertEqual(path.read_bytes(), binary)
            self.assertEqual(raw_artifact_size(path), len(binary))

    def test_sha256_remains_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lf_path = root / "lf.bin"
            crlf_path = root / "crlf.bin"
            lf_path.write_bytes(b"line\n")
            crlf_path.write_bytes(b"line\r\n")

            self.assertEqual(sha256(lf_path), hashlib.sha256(b"line\n").hexdigest())
            self.assertEqual(sha256(crlf_path), hashlib.sha256(b"line\r\n").hexdigest())
            self.assertNotEqual(sha256(lf_path), sha256(crlf_path))


if __name__ == "__main__":
    unittest.main()
