from __future__ import annotations

import copy
import os
import shutil
import subprocess
import tempfile
import unittest
from tests.fixed_user_assembly_fixture import historical_user_assembly
from pathlib import Path

from harness.bounded_user_argument import load_contract, validate_contract, response_digest
from harness.validators_impl.bounded_user_argument import validate_argument_sources, validate_argument_elf

ROOT = Path(__file__).resolve().parents[1]


class BoundedUserArgumentContractTests(unittest.TestCase):
    def test_successor_geometry(self):
        contract = load_contract()
        response = contract['response']
        self.assertEqual(contract['request']['size_bytes'], 40)
        self.assertEqual(response['size_bytes'], 96)
        self.assertEqual(response['result_offset'], 88)
        self.assertEqual(int(contract['consumption']['virtual_address'], 16)
                         - int(response['virtual_address'], 16) - 96, 32)

    def test_contract_rejects_boundary_mutations(self):
        mutations = [('wire_format_version', None, 1), ('request', 'size_bytes', 48),
                     ('request', 'payload_offset', 32), ('request', 'identifier', 3),
                     ('request', 'argument_max', 65536), ('request', 'flags', 1),
                     ('request', 'reserved', 1), ('response', 'size_bytes', 88),
                     ('response', 'result_offset', 80), ('consumption', 'size_bytes', 56),
                     ('consumption', 'response_digest_qwords', 11),
                     ('runtime', 'sessions', 3), ('validation', 'complete_cleanup_readback', False)]
        for section, field, value in mutations:
            with self.subTest(section=section, field=field):
                contract = copy.deepcopy(load_contract())
                if field is None:
                    contract[section] = value
                else:
                    contract[section][field] = value
                with self.assertRaises(ValueError):
                    validate_contract(contract)

    def test_unknown_field_rejected(self):
        contract = load_contract()
        contract['extra'] = True
        with self.assertRaises(ValueError):
            validate_contract(contract)

    def test_boolean_cannot_substitute_for_integer(self):
        contract = load_contract()
        contract['request']['reserved'] = False
        with self.assertRaises(ValueError):
            validate_contract(contract)

    def test_digest_covers_appended_result(self):
        original = list(range(12))
        altered = original.copy()
        altered[11] ^= 1
        self.assertNotEqual(response_digest(original), response_digest(altered))

    def test_truncated_digest_rejected(self):
        with self.assertRaises(ValueError):
            response_digest([0] * 11)


class BoundedUserArgumentExecutableTests(unittest.TestCase):
    def test_real_odin_service_boundaries(self):
        result = run_service_fixture()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_hardcoded_result_is_detected(self):
        result = run_service_fixture(('argument + BOUNDED_USER_ARGUMENT_INCREMENT', 'u64(8)'))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_missing_range_guard_is_detected(self):
        result = run_service_fixture(('argument > BOUNDED_USER_ARGUMENT_MAX', 'false'))
        self.assertNotEqual(result.returncode, 0, result.stdout)


class BoundedUserArgumentEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.privilege = historical_user_assembly((ROOT / 'kernel/arch/x86_64/privilege_transition.asm').read_text())
        self.layout = (ROOT / 'kernel/arch/x86_64/runtime_layout.inc').read_text()
        self.service = (ROOT / 'kernel/bounded_user_argument.odin').read_text()

    def test_historical_assembly_sources_validate(self):
        self.assertIsNone(validate_argument_sources(self.privilege, self.layout, self.service))

    def test_argument_boundary_mutations_fail(self):
        mutations = (
            ('mov rdi, [rel fixed_user_request_shadow + 24]', 'mov rdi, [FIXED_USER_REQUEST_VA + 24]'),
            ('cmp qword [rel fixed_user_request_shadow + 24], FIXED_USER_ARGUMENT_MAX', 'nop'),
            ('call evaluate_bounded_user_argument', 'xor eax, eax'),
            ('call validate_fixed_user_argument_result', 'xor eax, eax'),
            ('cmp [rdi + 88], rax', 'cmp rax, rax'),
            ('xor rax, [rdi + 88]', 'nop'),
            ('mov rax, [rsi + 88]', 'xor eax, eax'),
            ('%define FIXED_USER_RESPONSE_QWORDS (FIXED_USER_RESPONSE_SIZE / 8)', '%define FIXED_USER_RESPONSE_QWORDS 11'),
            ('mov ecx, FIXED_USER_RESPONSE_QWORDS', 'mov ecx, 11'),
            ('mov rdi, FIXED_USER_DATA_SCRATCH_VA', 'mov rdi, USER_PROBE_STACK_VA'),
            ('cmp qword [rdi + 80], 0', 'cmp rax, rax'),
        )
        for before, after in mutations:
            with self.subTest(mutation=before):
                self.assertIn(before, self.privilege)
                changed = self.privilege.replace(before, after)
                self.assertIsNotNone(validate_argument_sources(changed, self.layout, self.service))

    def test_old_response_size_rejected(self):
        layout = self.layout.replace('FIXED_USER_RESPONSE_SIZE 96', 'FIXED_USER_RESPONSE_SIZE 88')
        self.assertIsNotNone(validate_argument_sources(self.privilege, layout, self.service))

    def test_unbounded_odin_range_rejected(self):
        service = self.service.replace('u64(65535)', 'u64(65536)')
        self.assertIsNotNone(validate_argument_sources(self.privilege, self.layout, service))

    def test_linked_service_evidence_required(self):
        valid = dict(service_present=True, builder_calls_service=True, result_validator_present=True)
        self.assertIsNone(validate_argument_elf(valid))
        for field in valid:
            with self.subTest(field=field):
                self.assertIsNotNone(validate_argument_elf(valid | {field: False}))


class HardwarePrimitiveCompatibilityTests(unittest.TestCase):
    def test_preserved_hardware_instruction_sequences(self):
        source = (ROOT / 'kernel/arch/x86_64/syscall.asm').read_text()
        expected = {
            'x86_read_timestamp': ['rdtsc', 'shl rdx, 32', 'or rax, rdx', 'ret'],
            'x86_halt': ['hlt', 'ret'],
            'x86_outb': ['mov edx, edi', 'mov al, sil', 'out dx, al', 'ret'],
            'x86_inb': ['mov edx, edi', 'in al, dx', 'ret'],
        }
        for name, instructions in expected.items():
            with self.subTest(primitive=name):
                body = source.split(name + ':\n', 1)[1].split('\n\n', 1)[0]
                self.assertEqual([line.strip() for line in body.splitlines()], instructions)


def run_service_fixture(mutation=None):
    source = (ROOT / 'kernel/bounded_user_argument.odin').read_text()
    if mutation:
        if mutation[0] not in source:
            raise AssertionError('Mutation must change actual production code')
        source = source.replace(*mutation)
    with tempfile.TemporaryDirectory(prefix='kozo argument ') as directory:
        root = Path(directory)
        (root / 'service.odin').write_text(source.replace('package kernel', 'package main', 1))
        (root / 'main.odin').write_text(SERVICE_TEST_MAIN)
        executable = root / ('argument-test.exe' if os.name == 'nt' else 'argument-test')
        build = subprocess.run([shutil.which('odin') or 'odin', 'build', str(root),
                                '-out:' + str(executable)],
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, timeout=90)
        if build.returncode != 0:
            raise AssertionError('Executable fixture must compile: ' + build.stdout)
        return subprocess.run([str(executable)], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, timeout=10)


SERVICE_TEST_MAIN = '''package main
main :: proc() {
    valid_arguments := []u64{0, 1, 7, 65535}
    for argument in valid_arguments {
        output := u64(0)
        status := evaluate_bounded_user_argument(argument, &output)
        assert(status == 0)
        assert(output == argument + 1)
    }
    invalid_arguments := []u64{65536, 0xffffffffffffffff}
    for argument in invalid_arguments {
        output := u64(99)
        status := evaluate_bounded_user_argument(argument, &output)
        assert(status == 1)
        assert(output == 0)
    }
}
'''
