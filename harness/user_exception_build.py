from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from harness.fixed_rust_user import read_sections, read_symbols, require

FAULT_SYMBOL = 'kozo_rust_user_fault_site'
USER_INITIAL_RSP = 0x0000400000002ff0


def write_stack_input(output: Path, compiler, command, response=False, control=0):
    evidence = derive_stack(output.read_bytes(), response, control)
    output_option = command.index('-o')
    evidence.update(compiler=compiler, target='x86_64-unknown-none',
                    compile_flags=command[1:output_option] + command[output_option + 3:],
                    fault_symbol=FAULT_SYMBOL)
    output.with_suffix('.stack.json').write_text(json.dumps(evidence, indent=2) + '\n')
    output.with_suffix('.stack.inc').write_text(
        '%define USER_EXCEPTION_EXPECTED_RSP ' + hex(evidence['expected_fault_rsp']) + '\n')
    return evidence


def derive_stack(content, response=False, control=0):
    sections = read_sections(content)
    symbols = read_symbols(sections)
    anchor = next(s for s in symbols if s['name'] == FAULT_SYMBOL)
    probe = sections[anchor['section']]['data']
    # Only this directly compiled, non-tail-call, frame-pointer shape is governed.
    prefix = bytes.fromhex('554889e5')
    extra_stack = 8 if control == 8 else 0
    if extra_stack:
        prefix += bytes.fromhex('6a00')
    prefix += bytes.fromhex('6a129d' if control == 33 else '6a029d')
    if control in (6, 19, 20, 21):
        prefix += bytes.fromhex('eb02')
    opcode = bytes.fromhex('0fb9c0' if control == 7 else '0f0b')
    require(probe.startswith(prefix + opcode), 'Unsupported compiled fault-probe shape')
    require(anchor['value'] == len(prefix), 'Fault anchor is not the normalized UD2 instruction')
    name = 'kozo_rust_user_response_entry' if response else 'kozo_rust_user_request_entry'
    entry = next(s for s in symbols if s['name'] == name)
    code = sections[entry['section']]['data']
    frame = compiled_frame_size(code)
    require(code[-5:] == b'\xe8\x00\x00\x00\x00', 'Fault call is not direct and terminal')
    require_direct_probe_reference(sections, symbols, entry, anchor, len(code) - 4)
    delta = 8 + 8 + frame + 8 + 8
    return dict(object_sha256=hashlib.sha256(content).hexdigest(),
                entry_symbol=name, frame_bytes=frame, derived_stack_delta=delta,
                control=control, observed_control_stack_delta=delta + extra_stack,
                expected_fault_rsp=USER_INITIAL_RSP - delta,
                call_offset=len(code) - 5, anchor_offset=anchor['value'])


def compiled_frame_size(code):
    require(code[:4] == bytes.fromhex('554889e5'), 'Unsupported Rust frame prologue')
    if code[4:7] == bytes.fromhex('4883ec'):
        return code[7]
    require(code[4:7] == bytes.fromhex('4881ec'), 'Missing bounded Rust frame allocation')
    return struct.unpack_from('<I', code, 7)[0]


def require_direct_probe_reference(sections, symbols, entry, anchor, offset):
    references = []
    for section in sections:
        if section['type'] == 4 and section['info'] == entry['section']:
            references.extend(struct.unpack_from('<QQq', section['data'], position)
                              for position in range(0, section['size'], 24))
    require(len(references) == 1, 'Ambiguous fixture call graph')
    location, info, addend = references[0]
    target = symbols[info >> 32]
    require(location == offset and (info & 0xffffffff) == 4 and addend == -4,
            'Unsupported fixture call relocation')
    require(target['section'] == anchor['section'] and target['value'] == 0,
            'Fixture call does not reach the Rust fault routine')
