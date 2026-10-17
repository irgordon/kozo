from pathlib import Path
import copy
import json
import tempfile
import unittest

from harness.fixed_rust_user import build_user_object
from harness.user_exception_build import derive_stack
from harness.user_exception_evidence import (
    FRAME_GUARDS, production_image_issue, recovery_source_issue, validate_stack_evidence,
)
from harness.validators_impl.schema import validate_named_document
from tests.run_user_exception_controls import CONTROLS, fixture_instruction_issue, control_issue, recovery_issue

ROOT = Path(__file__).resolve().parents[1]


class BoundedUserExceptionSourceTests(unittest.TestCase):
    def test_exception_flags_are_exact_and_transaction_flags_unchanged(self):
        assembly = (ROOT / 'kernel/arch/x86_64/privilege_transition.asm').read_text()
        recovery = (ROOT / 'kernel/arch/x86_64/exception_recovery.inc').read_text()
        self.assertIn('%define USER_RFLAGS 0x2', assembly)
        self.assertIn('%define USER_EXCEPTION_RFLAGS 0x10002', recovery)
        self.assertIn('cmp qword [r15 + 16], USER_EXCEPTION_RFLAGS', recovery)
        self.assertNotIn('and qword [r15 + 16]', recovery)

    def test_record_mapping_is_checked_before_user_entry(self):
        assembly = (ROOT / 'kernel/arch/x86_64/privilege_transition.asm').read_text()
        entry = assembly.split('validate_user_probe_entry:', 1)[1].split('require_supervisor_rw_nx:', 1)[0]
        self.assertIn('lea rdi, [rel bounded_user_exception_record]\n    call require_supervisor_rw_nx', entry)

    def test_handler_aligns_trusted_frame_before_helpers(self):
        source = (ROOT / 'kernel/arch/x86_64/exception_recovery.inc').read_text()
        handler = source.split('bounded_user_exception_handler:', 1)[1].split('finish_authorized_user_exception:', 1)[0]
        self.assertLess(handler.index('cmp r15, rax'), handler.index('sub rsp, 8'))
        self.assertLess(handler.index('sub rsp, 8'), handler.index('call walk_page_mapping'))
        wrapper = source.split('finish_authorized_user_exception:', 1)[1].split('observe_bounded_user_exception:', 1)[0]
        self.assertIn('sub rsp, 8', wrapper)
        self.assertIn('add rsp, 8\n    ret', wrapper)

    def test_rust_normalizes_flags_at_exact_anchor(self):
        rust = (ROOT / 'userspace/fixed_user_program/user.rs').read_text()
        self.assertIn('"push 2", "popfq",', rust)
        self.assertIn('".set kozo_rust_user_fault_site, 2f"', rust)
        self.assertIn('"2:",', rust)
        self.assertIn('".else", "ud2", ".endif"', rust)
        self.assertIn('#[cfg(kozo_fault_fixture)]', rust)

    def test_rejection_does_not_use_continuation_or_failure_commit(self):
        recovery = (ROOT / 'kernel/arch/x86_64/exception_recovery.inc').read_text()
        rejection = recovery.split('reject_user_exception:', 1)[1].split('section .rodata', 1)[0]
        self.assertNotIn('saved_odin_return_stack', rejection)
        self.assertNotIn('commit_fixed_user_context', rejection)
        self.assertNotIn('call ', rejection)
        self.assertIn('FIXED_USER_CONTEXT_CLEARED', rejection)
        self.assertIn('cmp qword [rdi], 0', rejection)
        self.assertIn('jmp boot_terminal_halt', rejection)

    def test_each_frame_guard_is_required_in_order(self):
        source = (ROOT / 'kernel/arch/x86_64/exception_recovery.inc').read_text()
        self.assertIsNone(recovery_source_issue(source))
        for guard in FRAME_GUARDS:
            with self.subTest(guard=guard):
                self.assertIsNotNone(recovery_source_issue(source.replace(guard, '', 1)))

    def test_rejection_cannot_use_saved_continuation_or_commit_result(self):
        source = (ROOT / 'kernel/arch/x86_64/exception_recovery.inc').read_text()
        for instruction in ('call clear_fixed_user_execution_context',
                            'mov rsp, [rel saved_odin_return_stack]',
                            'call commit_fixed_user_context_failure_result', 'ret'):
            with self.subTest(instruction=instruction):
                self.assertIsNotNone(recovery_source_issue(source.replace(
                    'reject_user_exception:', 'reject_user_exception:\n    ' + instruction)))

    def test_generic_page_and_protection_fault_cleanup_gap_is_not_hidden(self):
        assembly = (ROOT / 'kernel/arch/x86_64/privilege_transition.asm').read_text()
        sink = assembly.split('privilege_fault_sink:', 1)[1].split('privilege_double_fault_sink:', 1)[0]
        self.assertIn('jmp boot_terminal_halt', sink)
        self.assertNotIn('clear_fixed_user_execution_context', sink)
        self.assertIn('pre-existing discrepancy', (ROOT / 'docs/adr/0022-bounded-user-exception-recovery.md').read_text())


class BoundedExceptionContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((ROOT / 'contracts/bounded_user_exception_recovery_contract.v0.json').read_text())

    def test_current_contract_and_every_required_top_level_field(self):
        validate_named_document('bounded_user_exception_recovery_contract', self.contract)
        for key in self.contract:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.contract)
                del changed[key]
                with self.assertRaises(ValueError):
                    validate_named_document('bounded_user_exception_recovery_contract', changed)

    def test_every_normative_predicate_and_record_field_is_fixed(self):
        for parent in ('required_state', 'fault_site', 'record', 'fixture', 'rejection_policy'):
            for key in self.contract[parent]:
                with self.subTest(parent=parent, key=key):
                    changed = copy.deepcopy(self.contract)
                    changed[parent][key] = 'invalid_contract_mutation'
                    with self.assertRaises(ValueError):
                        validate_named_document('bounded_user_exception_recovery_contract', changed)

    def test_unknown_fields_and_taxonomy_changes_are_rejected(self):
        for parent in (None, 'required_state', 'fault_site', 'record', 'fixture', 'rejection_policy'):
            changed = copy.deepcopy(self.contract)
            (changed if parent is None else changed[parent])['arbitrary_return_pointer'] = 1
            with self.assertRaises(ValueError):
                validate_named_document('bounded_user_exception_recovery_contract', changed)

    def test_governed_controls_match_executable_fixture_catalog(self):
        evidence = self.contract['evidence']
        real = [name for name, (_, _, mechanism) in CONTROLS.items() if mechanism != 'synthetic']
        synthetic = [name for name, (_, _, mechanism) in CONTROLS.items() if mechanism == 'synthetic']
        self.assertEqual(evidence['real_controls'], real)
        self.assertEqual(evidence['synthetic_controls'], synthetic)
        for code in range(15):
            changed = copy.deepcopy(self.contract)
            changed['rejections'][code] = 'IGNORED_FAILURE'
            with self.assertRaises(ValueError):
                validate_named_document('bounded_user_exception_recovery_contract', changed)


class CompiledExceptionFixtureTests(unittest.TestCase):
    def test_real_pinned_object_derives_both_entry_stacks(self):
        with tempfile.TemporaryDirectory(prefix='kozo exception stack ') as directory:
            output = Path(directory) / 'fixed_user.o'
            build_user_object(ROOT, output, fault_fixture=True)
            request = derive_stack(output.read_bytes())
            response = derive_stack(output.read_bytes(), response=True)
            self.assertEqual(request['derived_stack_delta'], 80)
            self.assertEqual(response['derived_stack_delta'], 176)
            self.assertEqual(request['expected_fault_rsp'], 0x400000002fa0)
            self.assertEqual(response['expected_fault_rsp'], 0x400000002f40)
            evidence = json.loads(output.with_suffix('.stack.json').read_text())
            self.assertTrue(evidence['compiler'].startswith('rustc 1.96.0'))
            self.assertFalse(any(str(ROOT) in flag for flag in evidence['compile_flags']))
            validate_stack_evidence(evidence, output.read_bytes())
            for key, changed_value in (('object_sha256', '0' * 64),
                                       ('derived_stack_delta', 0),
                                       ('expected_fault_rsp', 0)):
                with self.subTest(field=key):
                    changed = evidence | {key: changed_value}
                    with self.assertRaises(ValueError):
                        validate_stack_evidence(changed, output.read_bytes())

    def test_ambiguous_or_changed_probe_code_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='kozo exception mutation ') as directory:
            output = Path(directory) / 'fixed_user.o'
            build_user_object(ROOT, output, fault_fixture=True)
            original = output.read_bytes()
            for before, after in ((bytes.fromhex('554889e56a029d'), bytes.fromhex('554889e5909090')),
                                  (bytes.fromhex('554889e54883ec30'), bytes.fromhex('554889e54883c430'))):
                with self.assertRaises(ValueError):
                    derive_stack(original.replace(before, after, 1))

    def test_extended_state_instructions_cannot_be_silently_accepted(self):
        self.assertIsNone(fixture_instruction_issue('0: pushq %rbp\n1: movq %rsp, %rbp\n4: ud2'))
        for instruction in ('movaps %xmm0, %xmm1', 'vzeroupper', 'fldl (%rax)',
                            'fxsave (%rax)', 'xrstor (%rax)', 'ldmxcsr (%rax)'):
            with self.subTest(instruction=instruction):
                self.assertIsNotNone(fixture_instruction_issue(instruction))


class ExceptionEvidencePolicyTests(unittest.TestCase):
    def test_production_fixture_symbols_or_enabled_site_fail(self):
        record = dict(authorized_rip=0, fixture_symbols=[], record_size=64,
                      record_aligned=True, record_rw_nx=True, record_disjoint=True,
                      handler_exact_rip_check=True, handler_exact_rflags_check=True)
        self.assertIsNone(production_image_issue(record))
        for key, value in (('authorized_rip', 1), ('fixture_symbols', ['select_user_exception_fixture']),
                           ('record_size', 32), ('record_aligned', False),
                           ('record_rw_nx', False), ('record_disjoint', False),
                           ('handler_exact_rip_check', False),
                           ('handler_exact_rflags_check', False)):
            with self.subTest(key=key):
                self.assertIsNotNone(production_image_issue(record | {key: value}))

    def test_rejection_requires_exact_structural_clear_and_no_result(self):
        for mode in (6, 8, 9, 13):
            evidence = rejection_fixture(mode)
            valid = evidence | {'serial': f'USER_EXCEPTION_REJECT={mode:02d}\n'}
            self.assertIsNone(control_issue(valid, 1, mode))
            for offset in range(32):
                changed = copy.deepcopy(valid)
                changed['memory']['context'][offset] ^= 1
                self.assertIsNotNone(control_issue(changed, 1, mode))
            changed = copy.deepcopy(valid)
            changed['memory']['result'][2] = 2
            self.assertIsNotNone(control_issue(changed, 1, mode))

    def test_emergency_halt_cannot_claim_verified_rejection_or_recovery(self):
        evidence = rejection_fixture(16)
        evidence['memory']['context'] = []
        evidence['memory']['context_raw'] = 'Cannot access memory'
        self.assertIsNone(control_issue(evidence, 1, 16))
        for diagnostic in ('USER_EXCEPTION_REJECT=01', 'USER_EXCEPTION_RECOVERED=06'):
            self.assertIsNotNone(control_issue(evidence | {'serial': diagnostic}, 1, 16))


def rejection_fixture(mode):
    rip = 0x4000000000cf
    stack = 0x400000002fa0
    observed_rip = rip + 2 if mode == 6 else rip
    observed_stack = stack - 8 if mode == 8 else stack
    events = []
    if mode == 9:
        events.append('0: v=81 e=0000 i=1 cpl=3 IP=0023:000040000000003e')
    events.append(f'1: v=06 e=0000 i=0 cpl=3 IP=0023:{observed_rip:016x} SP=001b:{observed_stack:016x}')
    return dict(terminal_halted=True, serial='', trace_events=events,
                authorized_rip=rip, stack={'expected_fault_rsp': stack},
                memory={'context_raw': '',
        'context': [1, 128, 0, 0, 4] + [0] * 27, 'result': [0] * 8})


if __name__ == '__main__':
    unittest.main()
