from __future__ import annotations

import subprocess
import os
import tempfile
import unittest
import json
import struct
import shutil
import copy
from pathlib import Path

from harness.fixed_rust_user import (
    build_user_object, inspect_object, read_sections, read_symbols, pinned_rustc,
    object_command, validate_relocations,
)
from harness.fixed_rust_user_evidence import (
    ENTRYPOINTS, SOURCE_RULES, current_execution_issue, machine_record, report_issue,
    source_issue,
)

ROOT = Path(__file__).resolve().parents[1]


class FixedRustUserBuildTests(unittest.TestCase):
    def test_real_pinned_object_has_closed_user_code(self):
        with tempfile.TemporaryDirectory(prefix='kozo rust user ') as directory:
            output = Path(directory) / 'fixed_user.o'
            evidence = build_user_object(ROOT, output)
            self.assertEqual(evidence['target'], 'x86_64-unknown-none')
            self.assertEqual(evidence['undefined_symbols'], [])
            self.assertLessEqual(evidence['allocated_bytes'], 4096)
            self.assertEqual(set(evidence['entrypoints']),
                             {'kozo_rust_user_request_entry', 'kozo_rust_user_response_entry'})
            self.assertEqual(inspect_object(output.read_bytes()), evidence['object'])
            content = output.read_bytes()
            for label, mutation in object_mutations(content):
                with self.subTest(label=label):
                    with self.assertRaises((ValueError, struct.error, IndexError)):
                        inspect_object(mutation)

    def test_actual_rust_request_response_tests(self):
        with tempfile.TemporaryDirectory(prefix='kozo rust policy ') as directory:
            executable = Path(directory) / ('policy.exe' if os.name == 'nt' else 'policy')
            subprocess.run([pinned_rustc(ROOT), '--edition', '2021', '--test', str(ROOT / 'userspace/fixed_user_program/user.rs'),
                            '-o', str(executable)], check=True, capture_output=True, timeout=90)
            result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class FixedRustUserEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.rust = (ROOT / 'userspace/fixed_user_program/user.rs').read_text()
        self.assembly = (ROOT / 'kernel/arch/x86_64/privilege_transition.asm').read_text()

    def test_current_rust_sources_are_valid(self):
        self.assertIsNone(source_issue(self.rust, self.assembly))

    def test_every_governed_wire_field_is_required(self):
        for rule in SOURCE_RULES:
            with self.subTest(rule=rule):
                self.assertIn(rule, self.rust)
                self.assertIsNotNone(source_issue(self.rust.replace(rule, '', 1), self.assembly))

    def test_each_cpl_and_response_guard_is_required(self):
        for before in ('if !at_cpl3()', 'if !response_is_valid(&response, argument)',
                       'construct_request();', 'write_consumption(consumption_words(&response));'):
            with self.subTest(before=before):
                self.assertIsNotNone(source_issue(self.rust.replace(before, '', 1), self.assembly))

    def test_compiled_rust_rejects_unconditional_response_acceptance(self):
        before = 'fn response_is_valid(words: &[u64; 12], argument: u64) -> bool {'
        result = run_mutated_rust_policy(self.rust.replace(before, before + '\n    return true;', 1))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_compiled_rust_rejects_missing_result_comparison(self):
        result = run_mutated_rust_policy(self.rust.replace('words[11] == argument + 1', 'true', 1))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_compiled_rust_rejects_nonzero_request_reserved_field(self):
        result = run_mutated_rust_policy(self.rust.replace('SEQUENCE, argument, 0]', 'SEQUENCE, argument, 1]', 1))
        self.assertNotEqual(result.returncode, 0, result.stdout)

    def test_assembly_must_call_both_rust_entries(self):
        for entry in ENTRYPOINTS:
            with self.subTest(entry=entry):
                self.assertIsNotNone(source_issue(self.rust, self.assembly.replace('call ' + entry, 'nop')))

    def test_legacy_assembly_cannot_replace_current_rust_execution(self):
        from tests.fixed_user_assembly_fixture import historical_user_assembly
        self.assertIsNotNone(source_issue(self.rust, historical_user_assembly(self.assembly)))

    def test_exact_stack_and_interrupt_guards_are_required(self):
        for before in ('test eax, eax', 'cmp rsp, rax', 'cmp rsp, rdx',
                       'push qword USER_RFLAGS', 'int KOZO_PRIVILEGE_RETURN_VECTOR'):
            with self.subTest(before=before):
                changed = self.assembly.replace(before, '', 1)
                self.assertIsNotNone(source_issue(self.rust, changed))

    def test_missing_elf_evidence_fails_closed(self):
        self.assertIsNotNone(current_execution_issue(ROOT, {}))

    def test_linked_evidence_rejects_wrong_page_bytes_calls_and_stack(self):
        record = json.loads((ROOT / 'artifacts/runtime/kernel_elf_report.json').read_text())['fixed_rust_user_execution']
        contract = json.loads((ROOT / 'contracts/fixed_rust_user_execution_contract.v0.json').read_text())
        self.assertIsNone(report_issue(record, self.rust, contract))
        mutations = (
            (('linked', 'page_size'), 8192), (('linked', 'page_flags'), 7),
            (('linked', 'entries', ENTRYPOINTS[0], 'inside_user_page'), False),
            (('linked', 'entries', ENTRYPOINTS[1], 'matches_object'), False),
            (('adapter_calls', 'user_privilege_probe_start'), False),
            (('machine', ENTRYPOINTS[0], 'nested_call_count'), 1),
            (('machine', ENTRYPOINTS[1], 'stack_peak_bytes'), 4100),
            (('machine', ENTRYPOINTS[1], 'compared_stack_offsets'), [8]),
            (('machine', ENTRYPOINTS[1], 'copy_bounds'), [12, 6]),
            (('object', 'architecture'), 'aarch64'),
            (('object', 'allocated_bytes'), 4097),
            (('object', 'undefined_symbols'), ['supervisor_only']),
        )
        for path, value in mutations:
            with self.subTest(path=path):
                changed = copy.deepcopy(record)
                parent = changed
                for key in path[:-1]:
                    parent = parent[key]
                parent[path[-1]] = value
                self.assertIsNotNone(report_issue(changed, self.rust, contract))

    def test_stack_peak_includes_call_return_address(self):
        instructions = [(0, 'pushq', '%rbp'), (1, 'subq', '$0x90, %rsp')]
        self.assertEqual(machine_record(instructions)['stack_peak_bytes'], 160)

    def test_baseline_cpu_and_nonredzone_abort_compilation_are_explicit(self):
        command = object_command('rustc', ROOT, Path('fixed_user.o'))
        for option in ('target-cpu=x86-64', 'no-redzone=yes', 'panic=abort', 'relocation-model=pic'):
            self.assertIn(option, command)
        self.assertIn('x86_64-unknown-none', command)

    def test_ungoverned_cpu_instruction_is_reported(self):
        for mnemonic in ('vmovdqa', 'xsave', 'rdrand', 'syscall'):
            with self.subTest(mnemonic=mnemonic):
                self.assertEqual(machine_record([(0, mnemonic, '')])['unsupported_instructions'], [mnemonic])

    def test_relocations_must_remain_pc_relative_and_inside_user_object(self):
        allocated = [{'index': 1}]
        symbols = [{'section': 0, 'name': ''}, {'section': 1, 'name': 'inside'}]
        relocation = dict(type=4, info=1, size=24, data=struct.pack('<QQq', 0, (1 << 32) | 2, -4))
        self.assertEqual(len(validate_relocations([relocation], symbols, allocated)), 1)
        absolute = relocation | {'data': struct.pack('<QQq', 0, (1 << 32) | 1, 0)}
        with self.assertRaisesRegex(ValueError, 'PC-relative'):
            validate_relocations([absolute], symbols, allocated)
        with self.assertRaisesRegex(ValueError, 'leaves'):
            validate_relocations([relocation], [symbols[0], symbols[1] | {'section': 2}], allocated)

    def test_llvm_and_gnu_instruction_spellings_match(self):
        operands = ['%cs, %ecx', '$0x90, %rsp', '%rcx, -0x8(%rbp)', '$0xc, %rcx']
        llvm = list(zip(range(4), ['movl', 'subq', 'cmpq', 'cmpq'], operands))
        gnu = list(zip(range(4), ['mov', 'sub', 'cmp', 'cmp'], operands))
        self.assertEqual(machine_record(llvm), machine_record(gnu))

    def test_rust_contract_matches_schema(self):
        from harness.validators_impl.schema import validate_named_document
        contract = json.loads((ROOT / 'contracts/fixed_rust_user_execution_contract.v0.json').read_text())
        self.assertIsNone(validate_named_document('fixed_rust_user_execution_contract', contract))

    def test_contract_rejects_changed_constants_and_unknown_authority(self):
        from harness.validators_impl.schema import validate_named_document
        contract = json.loads((ROOT / 'contracts/fixed_rust_user_execution_contract.v0.json').read_text())
        for field, value in contract.items():
            changed = contract | {field: None}
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_named_document('fixed_rust_user_execution_contract', changed)
        with self.assertRaises(ValueError):
            validate_named_document('fixed_rust_user_execution_contract', contract | {'kernel_pointer': 0})


def run_mutated_rust_policy(source):
    with tempfile.TemporaryDirectory(prefix='kozo Rust mutation ') as directory:
        fixture = Path(directory)
        user = fixture / 'userspace/fixed_user_program/user.rs'
        binding = fixture / 'bindings/rust/kozo_abi.rs'
        user.parent.mkdir(parents=True)
        binding.parent.mkdir(parents=True)
        user.write_text(source)
        shutil.copyfile(ROOT / 'bindings/rust/kozo_abi.rs', binding)
        executable = fixture / ('policy.exe' if os.name == 'nt' else 'policy')
        subprocess.run([pinned_rustc(ROOT), '--edition', '2021', '--test', str(user), '-o', str(executable)],
                       check=True, capture_output=True, timeout=90)
        return subprocess.run([str(executable)], capture_output=True, text=True, timeout=20)


def object_mutations(content):
    machine = bytearray(content)
    struct.pack_into('<H', machine, 18, 183)
    sections = read_sections(content)
    executable = next(section for section in sections if section['flags'] & 4 and section['size'])
    writable = bytearray(content)
    table_offset = struct.unpack_from('<Q', content, 40)[0]
    struct.pack_into('<Q', writable, table_offset + executable['index'] * 64 + 8, executable['flags'] | 1)
    oversized = bytearray(content + bytes(4096))
    struct.pack_into('<Q', oversized, table_offset + executable['index'] * 64 + 32, 4097)
    tls = bytearray(content)
    struct.pack_into('<Q', tls, table_offset + executable['index'] * 64 + 8, executable['flags'] | 1024)
    symbols = read_symbols(sections)
    entry_index = next(index for index, symbol in enumerate(symbols) if symbol['name'] == ENTRYPOINTS[0])
    table = next(section for section in sections if section['type'] == 2)
    undefined = bytearray(content)
    struct.pack_into('<H', undefined, table['offset'] + entry_index * 24 + 6, 0)
    return [('wrong-machine', machine), ('writable-user-code', writable),
            ('truncated-object', content[:24]), ('over-page-budget', oversized),
            ('tls-storage', tls), ('undefined-dependency', undefined)]


if __name__ == '__main__':
    unittest.main()
