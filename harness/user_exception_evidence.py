from __future__ import annotations

import hashlib
import json
import struct
import subprocess
from pathlib import Path

from harness.fixed_rust_user import read_sections, read_symbols, require
from harness.user_exception_build import compiled_frame_size
from harness.validators_impl.schema import validate_named_document

RECOVERY_PATH = Path('kernel/arch/x86_64/exception_recovery.inc')
CONTRACT_PATH = Path('contracts/bounded_user_exception_recovery_contract.v0.json')


def classify_qemu_rflags(contract, qmp_version, saved_flags, hosted_ubuntu=False):
    qemu = qmp_version.get('qemu', {}) if isinstance(qmp_version, dict) else {}
    triple = [qemu.get(field) for field in ('major', 'minor', 'micro')]
    version = '.'.join(str(part) for part in triple) if all(type(part) is int for part in triple) else None
    accepted = {int(value, 16) for value in contract['fault_site']['saved_exception_rflags']}
    profiles = contract['qemu_profiles']
    registered = version in profiles and version != 'hosted_ubuntu_24_04'
    form = ('architectural_rf_form' if saved_flags == int(contract['fault_site']['saved_exception_rflags'][1], 16)
            else 'legacy_qemu_live_flags_form' if saved_flags == int(contract['fault_site']['saved_exception_rflags'][0], 16)
            else 'invalid_frame_form')
    if version is None:
        blocker = 'QMP_VERSION_UNAVAILABLE'
    elif hosted_ubuntu and version != profiles['hosted_ubuntu_24_04']:
        blocker = 'HOSTED_QEMU_VERSION_DRIFT'
    elif registered and saved_flags != int(profiles[version], 16):
        blocker = 'QEMU_RFLAGS_PROFILE_MISMATCH'
    elif saved_flags not in accepted:
        blocker = 'BAD_RFLAGS'
    elif not registered and form == 'legacy_qemu_live_flags_form':
        blocker = 'QEMU_RFLAGS_UNREGISTERED_LEGACY_FORM'
    else:
        blocker = None
    return dict(qemu_upstream_version=version, qemu_package_string=qmp_version.get('package', '') if isinstance(qmp_version, dict) else '',
                saved_exception_rflags=hex(saved_flags), rflags_form=form,
                emulator_registration_status='registered' if registered else 'unregistered_emulator',
                profile_match=blocker is None, evidence_blocker=blocker)
FRAME_GUARDS = (
    'lea rax, [rel privilege_return_stack_top - 40]', 'cmp r15, rax',
    'mov rax, [r15 + 8]', 'and eax, 3', 'cmp eax, 3',
    'cmp qword [r15 + 8], USER_CODE_SELECTOR',
    'cmp qword [r15 + 32], USER_DATA_SELECTOR',
    'cmp qword [r15 + 16], USER_EXCEPTION_RFLAGS_LEGACY',
    'cmp qword [r15 + 16], USER_EXCEPTION_RFLAGS_ARCHITECTURAL',
    'mov rax, __kozo_authorized_ud2_rip', 'cmp [r15], rax',
    'call walk_page_mapping', 'call physical_for_kernel_virtual', 'cmp r13, rax',
    'cmp word [rax], 0x0b0f', 'cmp [r15 + 24], rax',
    'call validate_user_exception_continuation', 'call user_exception_record_is_empty',
)


def current_recovery_issue(root, report):
    try:
        validate_named_document('bounded_user_exception_recovery_contract',
                                json.loads((root / CONTRACT_PATH).read_text()))
        source = (root / RECOVERY_PATH).read_text()
        issue = recovery_source_issue(source, json.loads((root / CONTRACT_PATH).read_text()))
        if issue:
            return issue
        return production_image_issue(report.get('bounded_user_exception_recovery', {}))
    except (OSError, ValueError, KeyError) as error:
        return 'Missing or invalid bounded exception proof: ' + str(error)


def recovery_source_issue(source, contract=None):
    contract = contract or json.loads(CONTRACT_PATH.read_text())
    cursor = 0
    for guard in FRAME_GUARDS:
        cursor = source.find(guard, cursor)
        if cursor < 0:
            return 'Missing or reordered exception guard: ' + guard
        cursor += len(guard)
    for value, name in zip(contract['fault_site']['saved_exception_rflags'],
                           ('LEGACY', 'ARCHITECTURAL')):
        if f'%define USER_EXCEPTION_RFLAGS_{name} {value}' not in source:
            return 'Exception flags differ from the contract enumeration'
    if 'and qword [r15 + 16]' in source or 'or qword [r15 + 16]' in source:
        return 'Saved exception flags must not be masked or normalized'
    rejection = source.split('reject_user_exception:', 1)[-1].split('section .rodata', 1)[0]
    for forbidden in ('call ', 'mov rsp, [rel saved_odin_return_stack]',
                      'commit_fixed_user_context', 'ret\n'):
        if forbidden in rejection:
            return 'Rejection must not use a stack, continuation or trusted result'
    for required in ('rep stosq', 'FIXED_USER_CONTEXT_CLEARED', 'cmp qword [rdi], 0',
                     'USER_PROBE_DATA_VA', 'USER_PROBE_STACK_VA',
                     'fixed_user_context_result', 'saved_odin_return_stack',
                     'user_exception_emergency_halt:', 'jmp boot_terminal_halt'):
        if required not in rejection:
            return 'Rejection clearing/readback or emergency halt is missing'
    return None


def production_image_issue(record):
    if record.get('authorized_rip') != 0 or record.get('fixture_symbols') != []:
        return 'Production must contain no enabled fixture fault site or hook'
    if record.get('record_size') != 64 or not record.get('record_aligned'):
        return 'Recovery evidence record geometry is invalid'
    if not record.get('record_rw_nx') or not record.get('record_disjoint'):
        return 'Recovery evidence record placement is invalid'
    if not record.get('handler_exact_rip_check') or not record.get('handler_enumerated_rflags_check'):
        return 'Linked handler must enumerate exactly the two contract flags'
    if not record.get('int_0x81_exact_rflags_check'):
        return 'Ordinary int 0x81 frame must retain exact 0x2 flags'
    return None


def image_record(kernel):
    try:
        return inspect_image_record(kernel)
    except (OSError, ValueError, KeyError, StopIteration) as error:
        return {'error': str(error)}


def inspect_image_record(kernel):
    content = kernel.read_bytes()
    sections = read_sections(content)
    entries = read_symbols(sections)
    require(sum(entry['name'] == 'kozo_rust_user_fault_site' for entry in entries) <= 1,
            'Multiple approved Rust fault anchors')
    symbols = {entry['name']: entry for entry in entries}
    start = symbols['bounded_user_exception_record']['value']
    end = symbols['bounded_user_exception_record_end']['value']
    section = sections[symbols['bounded_user_exception_record']['section']]
    protected = (('boot_stack', 16384), ('boot_memory_region', 4096),
                 ('fixed_user_context', 128), ('fixed_user_context_result', 32),
                 ('repeated_user_session_coordinator', 32), ('privilege_return_stack', 4096),
                 ('double_fault_stack', 4096), ('governed_gdt', 56),
                 ('governed_tss', 104), ('governed_idt', 4096),
                 ('governed_page_tables_start', 28672),
                 ('fixed_user_request_shadow', 40), ('fixed_user_response_shadow', 96),
                 ('fixed_user_response_verify', 96), ('fixed_user_consumption_shadow', 48),
                 ('fixed_user_transaction_phase', 8))
    disjoint = all(end <= symbols[name]['value'] or start >= symbols[name]['value'] + size
                   for name, size in protected)
    fixture_symbols = sorted(name for name in symbols if
        'user_exception_fixture' in name or 'kozo_rust_user_fault_' in name)
    page = next(section for section in sections if section['name'] == '.user_probe_code')
    handler = linked_handler_checks(kernel, sections, symbols)
    record = dict(record_size=end - start, record_aligned=start % 8 == 0,
                  record_rw_nx=section['flags'] == 3 and
                      symbols['__kernel_bss_start']['value'] <= start < end <= symbols['__kernel_bss_end']['value'],
                  record_disjoint=disjoint,
                  authorized_rip=symbols['__kozo_authorized_ud2_rip']['value'],
                  fixture_symbols=fixture_symbols,
                  user_page_sha256=hashlib.sha256(page['data']).hexdigest()) | handler
    if 'kozo_rust_user_fault_site' in symbols:
        record['fixture'] = linked_fixture_record(kernel, sections, symbols, page)
    return record


def linked_fixture_record(kernel, sections, symbols, page):
    stack = json.loads((kernel.parents[3] / 'work/fixed_user.stack.json').read_text())
    object_bytes = (kernel.parents[3] / 'work/fixed_user.o').read_bytes()
    validate_stack_evidence(stack, object_bytes)
    anchor = symbols['kozo_rust_user_fault_site']['value']
    entry = symbols[stack['entry_symbol']]
    code = page['data'][entry['value'] - page['address']:entry['value'] - page['address'] + entry['size']]
    require(compiled_frame_size(code) == stack['frame_bytes'], 'Linked Rust stack allocation differs')
    offset = stack['call_offset']
    require(code[offset] == 0xe8, 'Linked fault call is not direct')
    target = entry['value'] + offset + 5 + struct.unpack_from('<i', code, offset + 1)[0]
    require(target + stack['anchor_offset'] == anchor, 'Linked fault call targets the wrong routine')
    fault_offset = anchor - page['address']
    require(0 <= fault_offset <= 4094, 'Linked Rust fault anchor is outside fixed RX page')
    actual = page['data'][fault_offset:fault_offset + 2].hex()
    require(actual == ('0fb9' if stack['control'] == 7 else '0f0b'), 'Wrong linked fault instruction')
    require(linked_handler_stack_check(sections, symbols, stack['expected_fault_rsp']),
            'Linked exception handler does not compare the derived exact RSP')
    return stack | dict(linked_rip=0x400000000000 + fault_offset,
                         linked_instruction_bytes=actual, linked_stack_verified=True,
                         linked_call_verified=True)


def validate_stack_evidence(stack, object_bytes):
    require(stack['object_sha256'] == hashlib.sha256(object_bytes).hexdigest(),
            'Fixture stack evidence belongs to a different Rust object')
    require(stack['derived_stack_delta'] == 32 + stack['frame_bytes'],
            'Fixture stack delta does not match the compiled frame')
    require(stack['expected_fault_rsp'] == 0x400000002ff0 - stack['derived_stack_delta'],
            'Expected fault stack disagrees with the compiled delta')


def linked_handler_checks(kernel, sections, symbols):
    handler = handler_code(sections, symbols)
    rip = symbols['__kozo_authorized_ud2_rip']['value']
    load = b'\x48\xb8' + struct.pack('<Q', rip) + b'\x48\x85\xc0'
    location = handler.find(load)
    saved_rip_compare = handler.find(b'\x49\x39\x07', location + len(load))
    values = json.loads(CONTRACT_PATH.read_text())['fault_site']['saved_exception_rflags']
    flags = (bytes.fromhex('49837f10') + bytes([int(values[0], 16)]) + bytes.fromhex('740e49817f10') +
             struct.pack('<I', int(values[1], 16)) + bytes.fromhex('0f85'))
    disassembly = subprocess.run(['objdump', '-d', str(kernel)], capture_output=True, text=True,
                                 check=True).stdout
    from scripts.kernel_elf_report import extract_function_disassembly
    instructions = extract_function_disassembly(disassembly,
        symbols['bounded_user_exception_handler']['value'],
        symbols['finish_authorized_user_exception']['value'])
    frame_compares = [line for line in instructions if '0x10(%r15)' in line.operands and
                      line.mnemonic.startswith('cmp')]
    disassembly_matches = (len(frame_compares) == 2 and
                           all(value in line.operands for value, line in zip(values, frame_compares)))
    transaction = sections[symbols['validate_fixed_ring3_frame']['section']]
    transaction_start = symbols['validate_fixed_ring3_frame']['value'] - transaction['address']
    transaction_code = transaction['data'][transaction_start:transaction_start + 128]
    int_flags = int(json.loads(CONTRACT_PATH.read_text())['fault_site']['existing_int_0x81_rflags'], 16)
    int_comparison = bytes.fromhex('49837f10') + bytes([int_flags])
    return dict(handler_exact_rip_check=(location >= 0 and handler.count(load) == 1
                                         and 0 <= saved_rip_compare - location <= 48),
                handler_enumerated_rflags_check=(handler.count(flags) == 1 and
                                                  handler.find(flags) < location and
                                                  disassembly_matches),
                int_0x81_exact_rflags_check=transaction_code.count(int_comparison) == 1)


def linked_handler_stack_check(sections, symbols, rsp):
    handler = handler_code(sections, symbols)
    check = b'\x48\xb8' + struct.pack('<Q', rsp) + bytes.fromhex('49394718')
    return handler.count(check) == 1


def handler_code(sections, symbols):
    section = sections[symbols['bounded_user_exception_handler']['section']]
    start = symbols['bounded_user_exception_handler']['value'] - section['address']
    end = symbols['finish_authorized_user_exception']['value'] - section['address']
    require(0 <= start < end <= len(section['data']), 'Invalid linked exception handler span')
    return section['data'][start:end]
