"""Bounded QEMU controls; writes only caller-selected fixture directories."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVILEGE = 'kernel/arch/x86_64/privilege_transition.asm'
LAYOUT = 'kernel/arch/x86_64/runtime_layout.inc'
SOURCE_DIRECTORIES = ('kernel', 'bindings', 'contracts', 'schemas', 'harness',
                      'scripts', 'boot', 'linker')
CONTROLS = (
    ('zero', LAYOUT, 'FIXED_USER_ARGUMENT_OPERAND 7', 'FIXED_USER_ARGUMENT_OPERAND 0', True),
    ('maximum', LAYOUT, 'FIXED_USER_ARGUMENT_OPERAND 7', 'FIXED_USER_ARGUMENT_OPERAND 65535', True),
    ('out_of_range', LAYOUT, 'FIXED_USER_ARGUMENT_OPERAND 7', 'FIXED_USER_ARGUMENT_OPERAND 65536', False),
    ('corrupted_result', PRIVILEGE,
     '    call prepare_user_response_resume\n',
     '    inc qword [rel fixed_user_response_shadow + 88]\n    call prepare_user_response_resume\n', False),
    ('consumer_corruption', PRIVILEGE,
     'user_response_consumer_start:\n',
     'user_response_consumer_start:\n    mov rax, FIXED_USER_RESPONSE_VA\n    inc qword [rax + 88]\n', False),
    ('short_digest', PRIVILEGE,
     '    xor rax, [rdi + 88]\n    mov [rsi + 32], rax',
     '    mov [rsi + 32], rax', False),
    ('short_cleanup', PRIVILEGE,
     'clear_fixed_user_response_transaction:\n    cld\n    xor eax, eax\n    mov rdi, FIXED_USER_RESPONSE_VA\n    mov ecx, FIXED_USER_RESPONSE_QWORDS',
     'clear_fixed_user_response_transaction:\n    cld\n    xor eax, eax\n    mov rdi, FIXED_USER_RESPONSE_VA\n    mov ecx, 11', False),
    ('user_change_after_copy', PRIVILEGE,
     '    call validate_fixed_user_request\n',
     '    mov rax, FIXED_USER_REQUEST_VA\n    mov qword [rax + 24], 65536\n    call validate_fixed_user_request\n', True),
)


def main():
    options = parse_options()
    results = [run_control(options.output, control) for control in CONTROLS]
    write_results(options.output, results)


def run_control(output, control):
    name, path, before, after, expected_pass = control
    fixture = prepare_fixture(output / name, path, before, after)
    build_fixture(fixture)
    metadata = boot_fixture(fixture)
    validate_outcome(metadata, expected_pass)
    result = dict(control=name, expected_pass=expected_pass, outcome=metadata['outcome'],
                  markers=metadata['observed_marker_count'], sessions=metadata['completed_session_count'],
                  final_marker=metadata['observed_markers'][-1] if metadata['observed_markers'] else None)
    print(json.dumps(result), flush=True)
    return result


def validate_outcome(metadata, expected_pass):
    markers = metadata['observed_markers']
    if expected_pass:
        assert metadata['outcome'] == 'pass', metadata
        assert len(markers) == 52 and metadata['completed_session_count'] == 2, metadata
        assert markers[-1] == 'KOZO_RUNTIME_RETURN_OK', metadata
    else:
        assert metadata['outcome'] == 'blocked', metadata
        assert 'KOZO_RUNTIME_RETURN_OK' not in markers, metadata
        assert markers.count('KOZO_RING3_ENTER') <= 1, metadata


def prepare_fixture(destination, path, before, after):
    destination.mkdir(parents=True, exist_ok=False)
    for directory in SOURCE_DIRECTORIES:
        shutil.copytree(ROOT / directory, destination / directory, ignore=shutil.ignore_patterns('__pycache__'))
    source = destination / path
    text = source.read_text()
    assert before in text, (path, before)
    source.write_text(text.replace(before, after, 1))
    return destination


def build_fixture(fixture):
    with (fixture / 'build.log').open('w') as log:
        subprocess.run(['bash', 'scripts/build_boot_image.sh'], cwd=fixture,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)


def boot_fixture(fixture):
    environment = os.environ | {'KOZO_BOOT_ISO': str(fixture / 'artifacts/runtime/boot_image/kozo.iso')}
    with (fixture / 'qemu.log').open('w') as log:
        subprocess.run(['bash', 'scripts/qemu_smoke.sh'], cwd=fixture, env=environment,
                       stdout=log, stderr=subprocess.STDOUT, check=False, timeout=40)
    return json.loads((fixture / 'artifacts/runtime/qemu_smoke.metadata.json').read_text())


def write_results(output, results):
    (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


def parse_options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


if __name__ == '__main__':
    main()
