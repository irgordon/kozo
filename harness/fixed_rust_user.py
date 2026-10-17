from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import tomllib
from pathlib import Path

ENTRYPOINTS = ('kozo_rust_user_request_entry', 'kozo_rust_user_response_entry')
TARGET = 'x86_64-unknown-none'
PAGE_SIZE = 4096


def build_user_object(root: Path, output: Path, fault_fixture=False, response_fault=False, control=0):
    compiler = pinned_rustc(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = object_command(compiler, root, output)
    if fault_fixture:
        command += ['--cfg', 'kozo_fault_fixture']
        controls = {6: 'kozo_fault_bad_rip', 7: 'kozo_fault_bad_bytes', 8: 'kozo_fault_bad_rsp',
                    19: 'kozo_fault_int6', 20: 'kozo_fault_pf', 21: 'kozo_fault_int6',
                    33: 'kozo_fault_rflags_bit4'}
        if control in controls:
            command += ['--cfg', controls[control]]
    subprocess.run(command, check=True, capture_output=True, text=True)
    content = output.read_bytes()
    result = inspect_object(content)
    evidence = result | {'target': TARGET, 'object': result,
                         'sha256': hashlib.sha256(content).hexdigest(),
                         'object_size_bytes': len(content),
                         'compiler': run_output([compiler, '--version'])}
    output.with_suffix('.json').write_text(json.dumps(evidence, indent=2) + '\n')
    if fault_fixture:
        from harness.user_exception_build import write_stack_input
        write_stack_input(output, evidence['compiler'], command, response_fault, control)
    return evidence


def inspect_object(content):
    require(content[:6] == b'\x7fELF\x02\x01', 'Rust object must be ELF64 little-endian')
    require(struct.unpack_from('<HH', content, 16) == (1, 62), 'Rust object must be x86-64 ET_REL')
    sections = read_sections(content)
    allocated = validate_allocated_sections(sections)
    symbols = read_symbols(sections)
    require(not [s for s in symbols if s['name'] and s['section'] == 0], 'Undefined Rust dependency')
    entries = validate_entrypoints(symbols, allocated)
    relocations = validate_relocations(sections, symbols, allocated)
    return dict(architecture='x86_64', allocated_bytes=sum(s['size'] for s in allocated),
                entrypoints=entries, undefined_symbols=[], relocation_count=len(relocations))


def linked_entry_record(object_bytes, kernel_bytes):
    inspect_object(object_bytes)
    object_sections = read_sections(object_bytes)
    kernel_sections = read_sections(kernel_bytes)
    object_symbols = read_symbols(object_sections)
    kernel_symbols = read_symbols(kernel_sections)
    user = next(s for s in kernel_sections if s['name'] == '.user_probe_code')
    entries = {}
    for name in ENTRYPOINTS:
        original = next(s for s in object_symbols if s['name'] == name)
        linked = next(s for s in kernel_symbols if s['name'] == name)
        relative = linked['value'] - user['address']
        data = object_sections[original['section']]['data']
        expected = data[original['value']:original['value'] + original['size']]
        actual = user['data'][relative:relative + linked['size']]
        entries[name] = dict(address=hex(linked['value']), size_bytes=linked['size'],
                             inside_user_page=0 <= relative < relative + linked['size'] <= PAGE_SIZE,
                             matches_object=actual == expected)
    return dict(entries=entries, page_size=user['size'], page_flags=user['flags'],
                object_sha256=hashlib.sha256(object_bytes).hexdigest())


def validate_allocated_sections(sections):
    allocated = [section for section in sections if section['flags'] & 2 and section['size']]
    require(0 < sum(section['size'] for section in allocated) <= PAGE_SIZE, 'Rust user object exceeds one page')
    for section in allocated:
        require(not section['flags'] & (1 | 1024), 'Rust user storage must be read-only and non-TLS')
        require(section['name'].startswith(('.text', '.rodata')), 'Unexpected Rust allocated section')
    return allocated


def validate_entrypoints(symbols, allocated):
    executable = {s['index'] for s in allocated if s['flags'] & 4}
    entries = {}
    for name in ENTRYPOINTS:
        symbol = next((s for s in symbols if s['name'] == name), None)
        require(symbol is not None and symbol['section'] in executable and symbol['size'] > 0,
                'Missing executable Rust entrypoint: ' + name)
        entries[name] = dict(size_bytes=symbol['size'], section_index=symbol['section'], offset=symbol['value'])
    return entries


def validate_relocations(sections, symbols, allocated):
    allowed = {section['index'] for section in allocated}
    relocations = []
    for section in sections:
        if section['type'] != 4 or section['info'] not in allowed:
            continue
        for offset in range(0, section['size'], 24):
            location, info, addend = struct.unpack_from('<QQq', section['data'], offset)
            require((info & 0xffffffff) in (2, 4), 'Rust user references must be PC-relative')
            symbol = symbols[info >> 32]
            require(symbol['section'] in allowed, 'Rust reference leaves its read-only user image')
            relocations.append((section['info'], location, symbol['name'], addend))
    return relocations


def read_sections(content):
    offset = struct.unpack_from('<Q', content, 40)[0]
    entry_size, count, names_index = struct.unpack_from('<HHH', content, 58)
    require(entry_size == 64 and 0 < count < 4096 and names_index < count, 'Invalid ELF section table')
    headers = [struct.unpack_from('<IIQQQQIIQQ', content, offset + index * 64) for index in range(count)]
    names = blob(content, headers[names_index][4], headers[names_index][5])
    return [section_record(content, names, index, header) for index, header in enumerate(headers)]


def read_symbols(sections):
    table = next((section for section in sections if section['type'] == 2), None)
    require(table is not None and table['entry_size'] == 24, 'Missing ELF symbol table')
    strings = sections[table['link']]['data']
    return [symbol_record(strings, struct.unpack_from('<IBBHQQ', table['data'], offset))
            for offset in range(0, table['size'], 24)]


def section_record(content, names, index, header):
    name, kind, flags, address, offset, size, link, info, alignment, entry_size = header
    return dict(index=index, name=cstring(names, name), type=kind, flags=flags,
                address=address, offset=offset, size=size, link=link, info=info,
                alignment=alignment, entry_size=entry_size,
                data=blob(content, offset, size) if kind != 8 else b'')


def symbol_record(strings, entry):
    name, info, other, section, value, size = entry
    return dict(name=cstring(strings, name), info=info, section=section, value=value, size=size)


def pinned_rustc(root):
    channel = tomllib.loads((root / 'rust-toolchain.toml').read_text())['toolchain']['channel']
    return run_output(['rustup', 'which', '--toolchain', channel, 'rustc'])


def object_command(compiler, root, output):
    return [compiler, '--crate-name', 'fixed_user', '--crate-type', 'lib', '--edition', '2021',
            '--target', TARGET, '--emit=obj', '-C', 'opt-level=s', '-C', 'panic=abort',
            '-C', 'target-cpu=x86-64',
            '-C', 'no-redzone=yes', '-C', 'relocation-model=pic', '-C', 'code-model=small',
            '-C', 'force-frame-pointers=yes', '-C', 'force-unwind-tables=no',
            '-o', str(output), str(root / 'userspace/fixed_user_program/user.rs')]


def run_output(command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout.strip()


def blob(content, offset, size):
    require(offset >= 0 and size >= 0 and offset + size <= len(content), 'Truncated ELF section')
    return content[offset:offset + size]


def cstring(content, offset):
    require(0 <= offset < len(content), 'Invalid ELF string offset')
    return content[offset:content.index(b'\0', offset)].decode('utf-8')


def require(condition, detail):
    if not condition:
        raise ValueError(detail)
