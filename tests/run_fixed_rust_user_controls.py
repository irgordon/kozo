"""Execute isolated guest controls; never modify the caller's runtime sources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
RUST = 'userspace/fixed_user_program/user.rs'
ASSEMBLY = 'kernel/arch/x86_64/privilege_transition.asm'
DIRECTORIES = ('kernel', 'bindings', 'contracts', 'schemas', 'harness', 'scripts',
               'boot', 'linker', 'userspace/fixed_user_program')
CONTROLS = (
    ('valid', RUST, 'const ARGUMENT: u64 = 7;', 'const ARGUMENT: u64 = 7;', None, 2),
    ('invalid_metadata', RUST, 'const WIRE_VERSION: u64 = 2;',
     'const WIRE_VERSION: u64 = 3;', 11, 0),
    ('invalid_operand', RUST, 'const ARGUMENT: u64 = 7;',
     'const ARGUMENT: u64 = 65536;', 11, 0),
    ('corrupted_response_result', ASSEMBLY, 'resume_fixed_user_response_consumer:\n',
     'resume_fixed_user_response_consumer:\n    mov rax, FIXED_USER_RESPONSE_VA\n'
     '    inc qword [rax + 88]\n', 21, 0),
    ('invalid_consumption_record', RUST,
     '[1 | (1 << 32), 48, response[2], response[4], digest, 0]',
     '[1 | (1 << 32), 48, response[2], response[4], digest, 1]', 23, 0),
    ('invalid_saved_rip', ASSEMBLY, 'validate_ring3_request_frame:\n',
     'validate_ring3_request_frame:\n    inc qword [r15]\n', 6, 0),
    ('invalid_user_stack', ASSEMBLY,
     'user_rust_request_interrupt:\n    mov rsp, USER_INITIAL_RSP\n',
     'user_rust_request_interrupt:\n    mov rsp, USER_INITIAL_RSP\n    sub rsp, 8\n', 6, 0),
    ('unexpected_rust_return', RUST, '    construct_request();',
     '    return abi::K_OK;', 11, 0),
    ('second_session_stale_state', ASSEMBLY,
     '    rep stosq\n    call fixed_user_context_is_uninitialized\n.done:',
     '    rep stosq\n    mov rdi, FIXED_USER_REQUEST_VA\n    mov byte [rdi], 1\n'
     '    call fixed_user_context_is_uninitialized\n.done:', 9, 1),
)


def main():
    options = parse_options()
    options.output.mkdir(parents=True, exist_ok=False)
    results = [run_control(options.output, control) for control in CONTROLS]
    write_results(options.output, results)
    if any(result['result'] != 'PASS' for result in results):
        raise SystemExit('Rust guest control failed; inspect preserved per-control evidence')


def run_control(output, control):
    name, path, before, after, failure_code, completed_sessions = control
    fixture = prepare_fixture(output / name, path, before, after)
    try:
        build_fixture(fixture)
        metadata, serial, status = boot_fixture(fixture)
        issue = outcome_issue(metadata, serial, status, failure_code, completed_sessions)
        result = dict(control=name, result='FAIL' if issue else 'PASS', issue=issue,
                      expected_failure_code=failure_code, qemu_script_status=status,
                      failure_codes=rejection_codes(serial), metadata=metadata,
                      iso_sha256=hashlib.sha256((fixture / 'artifacts/runtime/boot_image/kozo.iso').read_bytes()).hexdigest())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = dict(control=name, result='FAIL', issue=str(error))
    (fixture / 'control.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'metadata'}), flush=True)
    return result


def outcome_issue(metadata, serial, status, failure_code, completed_sessions):
    markers = metadata['observed_markers']
    serial_markers = re.findall(r'^KOZO_[A-Z0-9_]+\r?$', serial, re.MULTILINE)
    if markers != [marker.rstrip('\r') for marker in serial_markers]:
        return 'Serial evidence disagrees with QEMU metadata'
    if metadata['completed_session_count'] != completed_sessions:
        return 'Unexpected completed session count'
    if failure_code is None:
        if status != 0 or metadata['outcome'] != 'pass' or markers != list(get_smoke_marker_order()):
            return 'Valid Rust program did not complete all 52 markers'
        if rejection_codes(serial) or markers[-1] != 'KOZO_RUNTIME_RETURN_OK':
            return 'Valid Rust program emitted failure or omitted the final marker'
    else:
        if metadata['outcome'] != 'blocked':
            return 'Invalid program was accepted'
        if failure_code not in rejection_codes(serial):
            return 'Required kernel rejection was not observed; a timeout/fault is insufficient'
        if markers.count('KOZO_RING3_ENTER') != max(1, completed_sessions):
            return 'Rejected program started an unexpected session'
        if any(marker in markers for marker in ('KOZO_RUNTIME_RETURN_OK', 'KOZO_CAPABILITY_DISPATCH_ENTER')):
            return 'Kernel continued after a rejected user program'
    return None


def rejection_codes(serial):
    return [int(code, 16) for code in re.findall(r'^USER_BOUNDARY_FAILURE=([0-9a-f]{8})\r?$', serial, re.MULTILINE)]


def prepare_fixture(destination, path, before, after):
    destination.mkdir(parents=True, exist_ok=False)
    for directory in DIRECTORIES:
        shutil.copytree(ROOT / directory, destination / directory,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile(ROOT / 'rust-toolchain.toml', destination / 'rust-toolchain.toml')
    source = destination / path
    text = source.read_text()
    if before not in text:
        raise ValueError('Control must mutate actual production source: ' + path)
    source.write_text(text.replace(before, after, 1))
    return destination


def build_fixture(fixture):
    with (fixture / 'build.log').open('w') as log:
        subprocess.run(['bash', 'scripts/build_boot_image.sh'], cwd=fixture,
                       stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)


def boot_fixture(fixture):
    fixture = fixture.resolve()
    environment = os.environ | {'KOZO_BOOT_ISO': str(fixture / 'artifacts/runtime/boot_image/kozo.iso')}
    with (fixture / 'qemu.log').open('w') as log:
        execution = subprocess.run(['bash', 'scripts/qemu_smoke.sh'], cwd=fixture, env=environment,
                                   stdout=log, stderr=subprocess.STDOUT, check=False, timeout=40)
    runtime = fixture / 'artifacts/runtime'
    return (json.loads((runtime / 'qemu_smoke.metadata.json').read_text()),
            (runtime / 'qemu_smoke.log').read_text(), execution.returncode)


def write_results(output, results):
    (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')


def parse_options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    return parser.parse_args()


if __name__ == '__main__':
    main()
