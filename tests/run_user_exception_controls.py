"""Execute bounded exception fixtures and preserve hardware and supervisor evidence."""
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
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.fixed_rust_user import read_sections, read_symbols
from harness.runtime_evidence_taxonomy import get_smoke_marker_order
from harness.user_exception_evidence import classify_qemu_rflags

CONTRACT = json.loads((ROOT / 'contracts/bounded_user_exception_recovery_contract.v0.json').read_text())

CONTROLS = {
    'session_1': (1, 0, 'real'), 'session_2': (2, 0, 'real'),
    'bad_frame': (1, 1, 'synthetic'), 'bad_cs_rpl': (1, 2, 'synthetic'),
    'bad_cs_selector': (1, 3, 'synthetic'), 'bad_ss': (1, 4, 'synthetic'),
    'bad_rflags': (1, 5, 'synthetic'), 'unauthorized_rip': (1, 6, 'real'),
    'bad_ud2_bytes': (1, 7, 'real'), 'altered_rsp': (1, 8, 'real'),
    'wrong_phase': (1, 9, 'real'), 'context_inactive': (1, 10, 'synthetic'),
    'bad_session': (1, 11, 'synthetic'), 'transition_count': (1, 12, 'synthetic'),
    'no_continuation': (1, 13, 'synthetic'), 'invalid_record': (1, 14, 'synthetic'),
    'site_disabled': (1, 15, 'synthetic'), 'unsafe_supervisor': (1, 16, 'synthetic'),
    'kernel_ud': (1, 18, 'real'), 'user_int6': (1, 19, 'real'),
    'user_pf': (1, 20, 'real'), 'double_fault': (1, 21, 'real'),
    'cleanup_failure': (1, 22, 'synthetic'),
    'invalid_selector': (1, 24, 'synthetic'), 'stale_selector': (1, 25, 'synthetic'),
    'duplicate_failure_commit': (1, 26, 'synthetic'),
    'skipped_stage': (1, 27, 'synthetic'), 'stage_readback_failure': (1, 28, 'synthetic'),
    'early_diagnostic': (1, 30, 'synthetic'),
    'backward_stage': (1, 31, 'synthetic'),
    'bad_rflags_rf_only': (1, 32, 'synthetic'),
    'bad_rflags_bit4': (1, 33, 'real'),
    'bad_rflags_if': (1, 34, 'synthetic'),
    'bad_cs_rpl_and_bad_rflags': (1, 35, 'synthetic'),
    'corrupted_failure_result': (1, 36, 'synthetic'),
}


def main():
    options = parse_options()
    if set(CONTROLS) != set(CONTRACT['control_expectations']):
        raise ValueError('Control inventory differs from the authoritative contract')
    options.output.mkdir(parents=True, exist_ok=False)
    if options.replay:
        replay_hosted_fixture(options.replay, options.output, options.expected_control)
        return
    if options.baseline_kernel:
        compare_production_page(options.baseline_kernel, options.output)
    results = [execute_control(options.output, name) for name in options.control or CONTROLS]
    (options.output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    first_qmp = next((item['qmp'] for item in results if 'qmp' in item), {})
    qemu_binary = os.environ.get('KOZO_QEMU_BIN') or shutil.which('qemu-system-x86_64')
    provenance = subprocess.run([qemu_binary, '--version'], capture_output=True, text=True,
                                check=True).stdout.splitlines()[0]
    environment = dict(evidence_scope='hosted_ci' if os.environ.get('GITHUB_ACTIONS') else 'local_nonhosted',
                       qmp_version=first_qmp, qemu_binary_version=provenance,
                       declared_control_count=len(options.control or CONTROLS),
                       passed_control_count=sum(item['result'] == 'PASS' for item in results))
    (options.output / 'environment.json').write_text(json.dumps(environment, indent=2) + '\n')
    write_fixture_checksums(options.output)
    raise SystemExit(any(item['result'] != 'PASS' for item in results))


def replay_hosted_fixture(source, output, name):
    if name not in ('session_1', 'session_2'):
        raise ValueError('Hosted replay requires one authorized fault fixture')
    session, mode, _ = CONTROLS[name]
    evidence = boot_image(source, output)
    issue = control_issue(evidence, session, mode)
    evidence.update(control=name, result='FAIL' if issue else 'PASS', issue=issue)
    (output / 'replay.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps({key: evidence.get(key) for key in ('control', 'result', 'issue')}))
    raise SystemExit(bool(issue))


def execute_control(output, name):
    directory = (output / name).resolve()
    directory.mkdir()
    session, mode, mechanism = CONTROLS[name]
    environment = os.environ | {'KOZO_RUNTIME_OUTPUT': str(directory),
                                'KOZO_FAULT_SESSION': str(session), 'KOZO_FAULT_MODE': str(mode)}
    try:
        build_image(directory, environment)
        evidence = boot_image(directory)
        issue = control_issue(evidence, session, mode)
        expected_mechanism, expected_code, expected_outcome = CONTRACT['control_expectations'][name]
        observed_outcome = observed_primary_outcome(evidence, mode)
        observed_codes = {outcome: code for _, code, outcome in CONTRACT['control_expectations'].values()}
        evidence.update(expected_primary_outcome=expected_outcome,
                        expected_primary_code=expected_code,
                        observed_primary_outcome=observed_outcome,
                        observed_primary_code=observed_codes.get(observed_outcome))
        if (mechanism != expected_mechanism or evidence['observed_primary_outcome'] != expected_outcome or
                evidence['observed_primary_code'] != expected_code):
            issue = issue or 'Primary outcome differs from the contract'
        evidence.update(control=name, mechanism=mechanism, result='FAIL' if issue else 'PASS', issue=issue)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        evidence = dict(control=name, mechanism=mechanism, result='FAIL', issue=str(error))
    (directory / 'control.json').write_text(json.dumps(evidence, indent=2) + '\n')
    write_fixture_checksums(directory)
    print(json.dumps({key: evidence.get(key) for key in ('control', 'mechanism', 'result', 'issue')}), flush=True)
    return evidence


def compare_production_page(baseline, output):
    from harness.user_exception_evidence import image_record, production_image_issue
    current = ROOT / 'artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf'
    before = next(s['data'] for s in read_sections(baseline.read_bytes()) if s['name'] == '.user_probe_code')
    after = next(s['data'] for s in read_sections(current.read_bytes()) if s['name'] == '.user_probe_code')
    issue = production_image_issue(image_record(current))
    if before != after or issue:
        raise ValueError(issue or 'Production user page differs from rebuilt starting baseline')
    evidence = dict(baseline_commit='99d3912a63fbb614f853b83992ec5387b92c7e54',
                    baseline_page_sha256=hashlib.sha256(before).hexdigest(),
                    production_page_sha256=hashlib.sha256(after).hexdigest(),
                    byte_identical=True, fixture_hooks_absent=True, authorized_rip=0)
    (output / 'production-page.json').write_text(json.dumps(evidence, indent=2) + '\n')


def write_fixture_checksums(directory):
    source = directory / 'source'
    source.mkdir(exist_ok=True)
    for name in ('userspace/fixed_user_program/user.rs', 'kernel/arch/x86_64/exception_recovery.inc',
                 'kernel/arch/x86_64/privilege_transition.asm', 'linker/kernel.ld',
                 'linker/exception_fixture.ld', 'linker/exception_fixture_disabled.ld'):
        shutil.copyfile(ROOT / name, source / Path(name).name)
    files = sorted(path for path in directory.rglob('*') if path.is_file() and path.name != 'SHA256SUMS')
    lines = [hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(directory).as_posix()
             for path in files]
    (directory / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')


def build_image(directory, environment):
    with (directory / 'build.log').open('w') as log:
        subprocess.run(['bash', 'scripts/build_boot_image.sh'], cwd=ROOT, env=environment,
                       stdout=log, stderr=subprocess.STDOUT, timeout=120, check=True)
    disassembly = subprocess.run(['objdump', '-d', str(directory / 'boot_image/work/fixed_user.o')],
                                 check=True, capture_output=True, text=True).stdout
    (directory / 'rust.disassembly.txt').write_text(disassembly)
    if fixture_instruction_issue(disassembly):
        raise ValueError('Fixture contains unexpected extended-state instructions')


def boot_image(directory, capture=None):
    capture = capture or directory
    kernel = directory / 'boot_image/image-root/boot/kozo/kozo-kernel.elf'
    symbols = {s['name']: s['value'] for s in read_symbols(read_sections(kernel.read_bytes()))}
    iso = directory / 'boot_image/kozo.iso'
    command = [os.environ.get('KOZO_QEMU_BIN') or shutil.which('qemu-system-x86_64'),
               '-machine', 'q35', '-accel', 'tcg', '-m', '256M', '-cpu', 'qemu64',
               '-display', 'none', '-monitor', 'none', '-qmp', 'stdio',
               '-serial', 'file:' + str(capture / 'serial.log'), '-no-reboot', '-no-shutdown',
               '-d', 'int,cpu_reset', '-D', str(capture / 'qemu-int.log'), '-cdrom', str(iso)]
    with (capture / 'stderr.log').open('w') as error:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=error, text=True)
        try:
            greeting = json.loads(process.stdout.readline())
            qmp_command(process, 'qmp_capabilities')
            registers = wait_for_terminal(process, capture)
            memory = capture_supervisor_memory(process, symbols)
            (capture / 'memory.json').write_text(json.dumps(memory, indent=2) + '\n')
            (capture / 'registers.txt').write_text(registers)
            qmp_command(process, 'quit')
            status = process.wait(timeout=2)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    serial = (capture / 'serial.log').read_text(errors='replace')
    trace = (capture / 'qemu-int.log').read_text(errors='replace')
    qmp_version = greeting['QMP']['version']
    frame_flags = memory['hardware_frame'][4] | (memory['hardware_frame'][5] << 32) if len(memory['hardware_frame']) >= 6 else 0
    fault_events = trace_event_lines(trace)
    profile = classify_qemu_rflags(CONTRACT, qmp_version, frame_flags,
                                   hosted_ubuntu=bool(os.environ.get('KOZO_HOSTED_UBUNTU_24_04')))
    if not any('v=06' in event and 'i=0 cpl=3' in event for event in fault_events):
        profile.update(rflags_form='not_applicable', profile_match=None,
                       evidence_blocker=profile['evidence_blocker'] if profile['evidence_blocker'] in
                       ('QMP_VERSION_UNAVAILABLE', 'HOSTED_QEMU_VERSION_DRIFT') else None)
    return dict(qemu_exit=status, qmp=qmp_version, **profile,
                iso_sha256=hashlib.sha256(iso.read_bytes()).hexdigest(),
                authorized_rip=symbols['__kozo_authorized_ud2_rip'],
                serial=serial, trace_events=fault_events,
                post_exception_reset='CPU Reset' in trace[trace.find('v=06'):],
                stack=json.loads((directory / 'boot_image/work/fixed_user.stack.json').read_text()),
                elf=json.loads((directory / 'kernel_elf_report.json').read_text()).get('bounded_user_exception_recovery'),
                memory=memory, terminal_halted=terminal_registers_match(registers, symbols['boot_terminal_halt']))


def wait_for_terminal(process, directory):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        time.sleep(0.1)
        serial = (directory / 'serial.log').read_text(errors='replace')
        if not any(line in serial for line in ('USER_EXCEPTION_', 'USER_BOUNDARY_FAILURE=')):
            continue
        registers = qmp_command(process, 'human-monitor-command', {'command-line': 'info registers'})
        if 'HLT=1' in registers:
            return registers
    return qmp_command(process, 'human-monitor-command', {'command-line': 'info registers'})


def capture_supervisor_memory(process, symbols):
    spans = {'context': ('fixed_user_context', 32),
             'result': ('fixed_user_context_result', 8),
             'record': ('bounded_user_exception_record', 16),
             'request_shadow': ('fixed_user_request_shadow', 10),
             'response_shadow': ('fixed_user_response_shadow', 24),
             'response_verify': ('fixed_user_response_verify', 24),
             'consumption_shadow': ('fixed_user_consumption_shadow', 12)}
    spans.update(transaction_phase=('fixed_user_transaction_phase', 2),
                 request_success=('fixed_user_request_success_state', 2),
                 privilege_probe=('privilege_probe_state', 2),
                 saved_continuation=('saved_odin_return_stack', 2))
    memory = {}
    for name, (symbol, count) in spans.items():
        text = qmp_command(process, 'human-monitor-command',
                           {'command-line': f'x /{count}wx 0x{symbols[symbol]:x}'})
        memory[name] = parse_memory_words(text)
        memory[name + '_raw'] = text
    text = qmp_command(process, 'human-monitor-command',
                       {'command-line': f'x /10wx 0x{symbols["privilege_return_stack_top"] - 40:x}'})
    memory['hardware_frame'] = parse_memory_words(text)
    for name, address in (('user_data', 0x400000001000), ('user_stack', 0x400000002000)):
        text = qmp_command(process, 'human-monitor-command',
                           {'command-line': f'x /1024wx 0x{address:x}'})
        memory[name] = parse_memory_words(text)
    return memory


def qmp_command(process, command, arguments=None):
    request = {'execute': command}
    if arguments is not None:
        request['arguments'] = arguments
    process.stdin.write(json.dumps(request) + '\n')
    process.stdin.flush()
    while True:
        response = json.loads(process.stdout.readline())
        if 'error' in response:
            raise ValueError(response['error'])
        if 'return' in response:
            return response['return']


def parse_memory_words(text):
    return [int(word, 16) for line in text.splitlines() if ':' in line
            for word in re.findall(r'0x([0-9a-fA-F]{8})\b', line.split(':', 1)[1])]


def trace_event_lines(text):
    return [line for line in text.splitlines() if re.search(r'\bv=[0-9a-f]{2}\b', line)]


def terminal_registers_match(text, address):
    match = re.search(r'RIP=([0-9a-f]+)', text)
    return 'HLT=1' in text and match is not None and address <= int(match[1], 16) <= address + 8


def fixture_instruction_issue(text):
    from scripts.kernel_elf_report import parse_disassembly_instructions
    registers = re.compile(r'%(?:xmm\d+|ymm\d+|zmm\d+|mm[0-7]|st\b)')
    extended = re.compile(r'^(?:v[a-z0-9]+|xsave[a-z]*|xrstor[a-z]*|fxsave[a-z]*|fxrstor[a-z]*|f[a-z]+|ldmxcsr|stmxcsr|emms)$')
    for _, mnemonic, operands in parse_disassembly_instructions(text):
        if registers.search(operands) or extended.fullmatch(mnemonic):
            return mnemonic
    return None


def control_issue(evidence, session, mode):
    if not evidence['terminal_halted']:
        return 'Guest did not reach a terminal halt within the unchanged 20-second bound'
    if evidence.get('evidence_blocker') in ('QMP_VERSION_UNAVAILABLE', 'HOSTED_QEMU_VERSION_DRIFT'):
        return evidence['evidence_blocker']
    if mode not in (5, 32, 33, 34, 35) and evidence.get('evidence_blocker'):
        return evidence['evidence_blocker']
    serial, memory = evidence['serial'], evidence['memory']
    markers = re.findall(r'^KOZO_[A-Z0-9_]+\r?$', serial, re.MULTILINE)
    markers = [marker.rstrip('\r') for marker in markers]
    expected = list(get_smoke_marker_order())
    if markers != expected[:len(markers)] or 'KOZO_RUNTIME_RETURN_OK' in markers:
        return 'Fault control did not preserve the exact failure prefix'
    if mode == 0:
        return recovery_issue(evidence, session)
    if 'USER_EXCEPTION_RECOVERED=06' in serial:
        return 'Rejected fault was reported as recovered'
    if mode in range(1, 16) or mode in (18, 32, 33, 34, 35):
        reason = 2 if mode in (18, 35) else 5 if mode in (32, 33, 34) else mode
        if f'USER_EXCEPTION_REJECT={reason:02d}' not in serial:
            return 'Missing exact rejection classification'
        if memory['context'] != [1, 128, 0, 0, 4] + [0] * 27:
            return 'Rejected exception did not preserve verified CLEARED representation'
        if any(memory['result']):
            return 'Rejected exception committed a lifecycle result'
        if 'USER_BOUNDARY_FAILURE=' in serial or 'USER_EXCEPTION_STAGE=' in serial:
            return 'Rejected exception returned through a trusted wrapper'
        issue = rejected_hardware_issue(evidence, mode)
        if issue:
            return issue
    if mode == 16 and 'USER_EXCEPTION_REJECT=' in serial:
        return 'Unsafe supervisor condition falsely claimed verified rejection cleanup'
    if mode == 16 and (memory['context'] or 'Cannot access memory' not in memory['context_raw']):
        return 'Emergency control did not demonstrate inaccessible context memory'
    if mode == 22 and memory['record'][2] != 3:
        return 'Failed cleanup advanced beyond its verified stage'
    if mode in (22, 26, 27, 28, 30, 31, 36):
        expected_stage = {22: 3, 26: 2, 27: 1, 28: 3, 30: 2, 31: 2, 36: 2}[mode]
        if memory['record'][2] != expected_stage or memory['context'] != [1, 128, 0, 0, 4] + [0] * 27:
            return 'Failed recovery stage advanced or retained context authority'
    safe_rejection = set(range(1, 16)) | {18, 22, 26, 27, 28, 30, 31, 32, 33, 34, 35, 36}
    if mode in safe_rejection:
        if memory['context'] != [1, 128, 0, 0, 4] + [0] * 27 or any(memory['result']):
            return 'Safe rejection left context authority or a trusted result'
        for name, length in (('user_data', 1024), ('user_stack', 1024),
                             ('request_shadow', 10), ('response_shadow', 24),
                             ('response_verify', 24), ('consumption_shadow', 12),
                             ('transaction_phase', 2), ('request_success', 2),
                             ('privilege_probe', 2), ('saved_continuation', 2)):
            if memory[name] != [0] * length:
                return 'Safe rejection retained reusable state: ' + name
    if mode in (24, 25) and markers.count('KOZO_RING3_ENTER'):
        return 'Invalid selector permitted Ring3 entry'
    if mode in (19, 20, 21):
        vector = {19: '0d', 20: '0e', 21: '08'}[mode]
        if not any('v=' + vector in event for event in evidence['trace_events']):
            return 'Expected real terminal processor event was absent'
        if memory['context'][4] != 2:
            return 'Existing generic fault-sink cleanup discrepancy was concealed'
        if 'USER_EXCEPTION_REJECT=' in serial or 'USER_EXCEPTION_RECOVERED=' in serial:
            return 'Generic fault was misclassified as bounded recovery'
        if mode == 19 and any('v=06' in event and 'i=0' in event for event in evidence['trace_events']):
            return 'Software int 6 incorrectly produced a recoverable #UD'
    return None


def rejected_hardware_issue(evidence, mode):
    events = [event for event in evidence['trace_events'] if 'v=06' in event and 'i=0' in event]
    if len(events) != 1:
        return 'Rejected UD2 was not exactly one real fault-class #UD'
    event = events[0]
    if mode == 18:
        return None if 'cpl=0' in event else 'Kernel-origin UD2 did not execute at CPL0'
    if 'cpl=3' not in event:
        return 'Rejected Rust fault did not originate at CPL3'
    actual_rip = int(re.search(r'IP=0023:([0-9a-f]+)', event)[1], 16)
    actual_rsp = int(re.search(r'SP=001b:([0-9a-f]+)', event)[1], 16)
    frame = evidence['memory']['hardware_frame']
    if (frame[0] | (frame[1] << 32)) != actual_rip:
        return 'QMP hardware-frame RIP differs from the processor exception trace'
    if (frame[6] | (frame[7] << 32)) != actual_rsp:
        return 'QMP hardware-frame RSP differs from the processor exception trace'
    approved = evidence['authorized_rip']
    if mode == 6 and actual_rip == approved:
        return 'BAD_RIP control did not execute its second real UD2'
    if mode not in (6, 15) and actual_rip != approved:
        return 'Rejected fault did not execute the approved Rust anchor'
    if mode == 8 and actual_rsp != evidence['stack']['expected_fault_rsp'] - 8:
        return 'BAD_RSP control did not alter the real fault stack by one qword'
    if mode == 9 and (actual_rsp != evidence['stack']['expected_fault_rsp'] or
                      len([item for item in evidence['trace_events'] if 'v=81' in item]) != 1):
        return 'BAD_PHASE control did not reach the same anchor after one return'
    if mode == 7 and evidence['elf']['fixture']['linked_instruction_bytes'] != '0fb9':
        return 'BAD_UD2_BYTES control lacks the intended RX instruction mutation'
    return None


def recovery_issue(evidence, session):
    serial, memory = evidence['serial'], evidence['memory']
    if 'USER_EXCEPTION_RECOVERED=06' not in serial:
        return 'Authorized exception did not complete supervisor recovery'
    marker_count = len(re.findall(r'^KOZO_[A-Z0-9_]+\r?$', serial, re.MULTILINE))
    if marker_count != 24 + (session - 1) * 11:
        return 'Authorized fault did not occur at its exact session entry prefix'
    stages = [int(word, 16) for word in re.findall(r'USER_EXCEPTION_STAGE=([0-9a-f]+)', serial)]
    if stages != [1, 2, 3, 4, 5]:
        return 'Recovery stage trace is incomplete, skipped or repeated'
    if serial.index('USER_EXCEPTION_RECOVERED=06') < serial.index('USER_EXCEPTION_STAGE=0000000000000005'):
        return 'Recovery diagnostic preceded Odin observation'
    if memory['context'] != [1, 128, 0, 0, 4] + [0] * 27 or any(memory['result']):
        return 'Authorized cleanup or result reset was not verified'
    for name, length in (('user_data', 1024), ('user_stack', 1024), ('request_shadow', 10),
                         ('response_shadow', 24), ('response_verify', 24), ('consumption_shadow', 12)):
        if memory[name] != [0] * length:
            return 'Incomplete authoritative cleanup snapshot: ' + name
    expected_record = [1, 64, 5, 0x106, 6, session, 0, 0, 1, 0, 0x7fff] + [0] * 5
    if memory['record'] != expected_record:
        return 'QEMU memory does not match the completed recovery record'
    if evidence['saved_exception_rflags'] not in CONTRACT['fault_site']['saved_exception_rflags']:
        return 'Actual saved exception flags differ from the exact enumeration'
    frame = memory['hardware_frame']
    if frame[0] | (frame[1] << 32) != evidence['authorized_rip']:
        return 'Hardware-saved fault RIP differs from linker authority'
    if frame[6] | (frame[7] << 32) != evidence['stack']['expected_fault_rsp']:
        return 'Hardware-saved stack differs from compiled stack authority'
    events = evidence['trace_events']
    if not any(f'v=06 e=0000 i=0 cpl=3 IP=0023:{evidence["authorized_rip"]:016x}' in line for line in events):
        return 'No real CPL3 #UD at the linker-authorized instruction'
    if any('v=08' in line for line in events) or evidence['post_exception_reset']:
        return 'Recovery was followed by a double fault or reset'
    return None


def observed_primary_outcome(evidence, mode):
    serial = evidence.get('serial', '')
    rejection = re.search(r'USER_EXCEPTION_REJECT=(\d\d)', serial)
    if rejection:
        code = int(rejection[1])
        return CONTRACT['rejections'][code - 1] if 1 <= code <= 15 else None
    if 'USER_EXCEPTION_RECOVERED=06' in serial:
        return 'RECOVERY_COMPLETE'
    events = evidence.get('trace_events', [])
    for vector, outcome in (('v=08', 'DOUBLE_FAULT_TERMINAL'),
                            ('v=0d', 'USER_INT6_GP_TERMINAL'),
                            ('v=0e', 'USER_PAGE_FAULT_TERMINAL')):
        if any(vector in event for event in events):
            return outcome
    if mode == 16 and 'Cannot access memory' in evidence.get('memory', {}).get('context_raw', ''):
        return 'UNSAFE_SUPERVISOR_EMERGENCY_HALT'
    stage = evidence.get('memory', {}).get('record', [0, 0, 0])[2]
    staged = {22: (3, 'CLEANUP_VERIFICATION_FAILED'),
              26: (2, 'DUPLICATE_FAILURE_COMMIT_BLOCKED'),
              27: (1, 'SKIPPED_RECOVERY_STAGE_BLOCKED'),
              28: (3, 'STAGE_READBACK_FAILED'),
              30: (2, 'EARLY_RECOVERY_DIAGNOSTIC_BLOCKED'),
              31: (2, 'BACKWARD_RECOVERY_STAGE_BLOCKED'),
              36: (2, 'CORRUPTED_FAILURE_RESULT_BLOCKED')}
    if mode in staged and stage == staged[mode][0]:
        return staged[mode][1]
    if mode in (24, 25) and 'USER_BOUNDARY_FAILURE=' in serial:
        return 'FIXTURE_SELECTOR_INVALID' if mode == 24 else 'FIXTURE_SELECTOR_STALE'
    return None


def parse_options():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--control', action='append', choices=CONTROLS)
    parser.add_argument('--baseline-kernel', type=Path)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--expected-control', choices=('session_1', 'session_2'))
    return parser.parse_args()


if __name__ == '__main__':
    main()
