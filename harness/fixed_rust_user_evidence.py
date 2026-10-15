from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from harness.fixed_rust_user import ENTRYPOINTS, inspect_object, linked_entry_record

RUST_PATH = Path('userspace/fixed_user_program/user.rs')
ADAPTERS = ('user_privilege_probe_start', 'user_response_consumer_start')
SOURCE_RULES = (
    '#![cfg_attr(not(test), no_std)]',
    'const REQUEST: usize = 0x0000_4000_0000_1000;',
    'const RESPONSE: usize = 0x0000_4000_0000_1080;',
    'const CONSUMPTION: usize = 0x0000_4000_0000_1100;',
    'const ARGUMENT_SCRATCH: usize = 0x0000_4000_0000_1130;',
    'const ARGUMENT: u64 = 7;', 'const WIRE_VERSION: u64 = 2;',
    'const REQUEST_ID: u64 = 2;', 'const REQUEST_BYTES: u64 = 40;',
    'const RESPONSE_BYTES: u64 = 96;', 'const SEQUENCE: u64 = 1;',
    'selector & 3 == 3', 'for index in 0..5',
    'write_volatile((REQUEST as *mut u64).add(index), words[index]);',
    'write_volatile(ARGUMENT_SCRATCH as *mut u64, ARGUMENT);',
    '[WIRE_VERSION | (REQUEST_ID << 32), REQUEST_BYTES | (RESPONSE_BYTES << 32),',
    'SEQUENCE, argument, 0]', 'for index in 0..12',
    'words[index] = read_volatile((RESPONSE as *const u64).add(index));',
    'read_volatile(ARGUMENT_SCRATCH as *const u64)',
    'if argument > 65535',
    'words[0] == WIRE_VERSION | (REQUEST_ID << 32)',
    'words[1] == (RESPONSE_BYTES << 32) | u64::from(abi::K_OK)',
    'words[2] == SEQUENCE', 'words[3] == 5', 'words[4] == 63',
    'words[5] == 4096', 'words[6] == 3', 'words[7] == 3',
    'words[8] == 6', 'words[9] == 127', 'words[10] == 0',
    'words[11] == argument + 1',
    'response.iter().fold(0, |digest, word| digest ^ word)',
    '[1 | (1 << 32), 48, response[2], response[4], digest, 0]',
    'for index in 0..6',
    'write_volatile((CONSUMPTION as *mut u64).add(index), words[index]);',
)


def source_issue(rust, assembly):
    rust = rust.split('#[cfg(test)]\nmod tests', 1)[0]
    if any(token not in rust for token in SOURCE_RULES):
        return 'Rust must construct and validate every governed wire field'
    for name, steps in rust_entry_rules():
        body = rust.split('fn ' + name + '()', 1)[-1].split('\n}', 1)[0]
        if not ordered(body, steps):
            return 'Rust entry policy is incomplete: ' + name
    return adapter_issue(assembly)


def rust_entry_rules():
    return (
        (ENTRYPOINTS[0], ('if !at_cpl3()', 'return INVALID;', 'construct_request();', 'abi::K_OK')),
        (ENTRYPOINTS[1], ('if !at_cpl3()', 'return INVALID;', 'let response = read_response();',
                         'let argument = read_argument_scratch();',
                         'if !response_is_valid(&response, argument)', 'return INVALID;',
                         'write_consumption(consumption_words(&response));', 'abi::K_OK')),
    )


def adapter_issue(assembly):
    for adapter, entry, end in zip(ADAPTERS, ENTRYPOINTS,
                                   ('user_privilege_probe_end:', 'user_response_consumer_end:')):
        body = assembly.split(adapter + ':', 1)[-1].split(end, 1)[0]
        steps = ('push rax', 'pop rcx', 'cmp rsp, rdx', 'call ' + entry,
                 'test eax, eax', 'jnz ', 'mov rax, USER_INITIAL_RSP',
                 'cmp rsp, rax', 'jne ', 'mov rsp, USER_INITIAL_RSP',
                 'push qword USER_RFLAGS', 'popfq', 'int KOZO_PRIVILEGE_RETURN_VECTOR', 'ud2')
        if not ordered(body, steps):
            return 'Rust adapter must retain exact stack and interrupt guards: ' + adapter
    return None


def ordered(source, tokens):
    position = 0
    for token in tokens:
        position = source.find(token, position)
        if position < 0:
            return False
        position += len(token)
    return True


def object_record(root, kernel, instruction_sets):
    source = (root / RUST_PATH).read_bytes()
    object_bytes = (kernel.parents[3] / 'work/fixed_user.o').read_bytes()
    return dict(source_sha256=hashlib.sha256(source).hexdigest(),
                object=inspect_object(object_bytes),
                linked=linked_entry_record(object_bytes, kernel.read_bytes()),
                machine={name: machine_record(instruction_sets[name]) for name in ENTRYPOINTS})


def machine_record(instructions):
    comparisons = []
    copy_bounds = []
    stack_bytes = 8
    for _, mnemonic, operands in instructions:
        operands = operands.replace(' ', '').split('#')[0]
        if mnemonic.startswith('cmp'):
            offset = re.search(r'-(0x[0-9a-f]+|[0-9]+)\(%rbp\)$', operands)
            if offset:
                comparisons.append(int(offset[1], 0))
            immediate = re.match(r'\$(0x[0-9a-f]+|[0-9]+),%[a-z]+$', operands)
            if immediate:
                copy_bounds.append(int(immediate[1], 0))
        if mnemonic.startswith('push'):
            stack_bytes += 8
        if mnemonic.startswith('sub') and operands.endswith(',%rsp'):
            stack_bytes += int(operands.split(',')[0].removeprefix('$'), 0)
    return dict(instruction_count=len(instructions), stack_peak_bytes=stack_bytes,
                nested_call_count=sum(m.startswith('call') for _, m, _ in instructions),
                cpl_read_present=any('%cs' in op for _, _, op in instructions),
                unsupported_instructions=sorted({m for _, m, _ in instructions
                    if m.startswith(('v', 'xsave', 'xrstor', 'rdrand', 'rdseed', 'syscall', 'sysret', 'wrmsr', 'swapgs'))}),
                compared_stack_offsets=sorted(set(comparisons)), copy_bounds=copy_bounds)


def current_execution_issue(root, report, assembly=None):
    try:
        rust = (root / RUST_PATH).read_text()
        if assembly is None:
            assembly = (root / 'kernel/arch/x86_64/privilege_transition.asm').read_text()
        contract = json.loads((root / 'contracts/fixed_rust_user_execution_contract.v0.json').read_text())
        from harness.validators_impl.schema import validate_named_document
        validate_named_document('fixed_rust_user_execution_contract', contract)
        issue = source_issue(rust, assembly)
        if issue:
            return issue
        return report_issue(report.get('fixed_rust_user_execution', {}), rust, contract)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return 'Missing or malformed Rust execution evidence: ' + str(error)


def report_issue(record, rust, contract):
    if any(record.get('adapter_calls', {}).get(adapter) is not True for adapter in ADAPTERS):
        return 'Linked adapters must call their Rust entrypoints'
    if record.get('source_sha256') != hashlib.sha256(rust.encode()).hexdigest():
        return 'Rust source differs from the linked build evidence'
    linked = record.get('linked', {})
    if linked.get('page_size') != contract['code_size_bytes'] or linked.get('page_flags') != 6:
        return 'Rust entries must occupy the existing RX user page'
    for entry in ENTRYPOINTS:
        evidence = linked.get('entries', {}).get(entry, {})
        if not evidence.get('inside_user_page') or not evidence.get('matches_object'):
            return 'Rust entry bytes or placement invalid: ' + entry
    object_evidence = record.get('object', {})
    if (object_evidence.get('architecture') != 'x86_64'
            or not 0 < object_evidence.get('allocated_bytes', 0) <= contract['code_size_bytes']):
        return 'Rust object architecture or allocated size is invalid'
    if object_evidence.get('undefined_symbols') != []:
        return 'Rust user object has unresolved dependencies'
    for entry in ENTRYPOINTS:
        machine = record.get('machine', {}).get(entry, {})
        if (not machine.get('cpl_read_present') or machine.get('nested_call_count') != 0
                or machine.get('unsupported_instructions') != []
                or not 0 < machine.get('stack_peak_bytes', 0) <= contract['stack_budget_bytes']):
            return 'Rust entry must have bounded leaf stack usage and inspect CPL: ' + entry
    request = record['machine'][ENTRYPOINTS[0]]
    response = record['machine'][ENTRYPOINTS[1]]
    if 5 not in request['copy_bounds']:
        return 'Rust request must retain its five-qword copy'
    if response['compared_stack_offsets'] != list(range(8, 97, 8)):
        return 'Rust response must compare every packed response qword'
    if response['copy_bounds'].count(12) != 2 or 6 not in response['copy_bounds']:
        return 'Rust response must copy and digest twelve qwords and emit six record qwords'
    return None
