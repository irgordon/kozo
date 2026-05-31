from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import PROTOCOL_MISMATCH
from harness.validators_impl import protocol_validator
from harness.validators_impl.protocol_validator import ProtocolContractValidator


class ProtocolContractValidatorTests(unittest.TestCase):
    def test_fails_when_rust_heartbeat_syscall_reference_is_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            header_path = root / "kozo_abi.h"
            kernel_path = root / "main.odin"
            service_path = root / "main.rs"
            header_path.write_text("#define K_SYSCALL_NOP 0\n#define K_SYSCALL_DEBUG_HEARTBEAT 1\n")
            kernel_path.write_text("case abi.K_SYSCALL_NOP:\ncase abi.K_SYSCALL_DEBUG_HEARTBEAT:\n")
            service_path.write_text('extern "C" { fn syscall_entry(id: u64, payload: *mut abi::HeartbeatPayload) -> u64; }\nfn call() { syscall_entry(1, p); }\n')

            original_header = protocol_validator._HEADER_PATH
            original_kernel = protocol_validator._KERNEL_PATH
            original_service = protocol_validator._SERVICE_PATH
            protocol_validator._HEADER_PATH = header_path
            protocol_validator._KERNEL_PATH = kernel_path
            protocol_validator._SERVICE_PATH = service_path
            try:
                result = ProtocolContractValidator().validate({})
            finally:
                protocol_validator._HEADER_PATH = original_header
                protocol_validator._KERNEL_PATH = original_kernel
                protocol_validator._SERVICE_PATH = original_service

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, PROTOCOL_MISMATCH)


if __name__ == "__main__":
    unittest.main()
