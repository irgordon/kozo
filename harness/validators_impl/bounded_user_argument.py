from __future__ import annotations

from harness.bounded_user_argument import ROOT, load_contract


def argument_evidence_issue(context):
    try:
        load_contract()
        service = (ROOT / 'kernel/bounded_user_argument.odin').read_text()
    except (OSError, ValueError, KeyError) as error:
        return ('argument_contract_invalid', 'argument.contract', str(error))
    issue = validate_argument_sources(context.privilege, context.layout, service)
    if issue is not None:
        return issue
    return validate_argument_elf(context.report.get('bounded_user_argument', {}))


def validate_argument_sources(privilege, layout, service):
    for field, source, tokens in argument_source_rules(privilege, layout, service):
        if not ordered_tokens_present(source, tokens):
            return ('argument_boundary_invalid', 'argument.' + field,
                    'Missing or unordered argument boundary: ' + field)
    return None


def validate_argument_elf(evidence):
    for field in ('service_present', 'builder_calls_service', 'result_validator_present'):
        if evidence.get(field) is not True:
            return ('argument_elf_invalid', 'argument.elf.' + field,
                    'Linked argument evidence must prove ' + field)
    return None


def argument_source_rules(privilege, layout, service):
    return (
        ('layout', layout, ('%define FIXED_USER_RESPONSE_SIZE 96',
                           '%define FIXED_USER_REQUEST_VERSION 2',
                           '%define FIXED_USER_ARGUMENT_MAX 65535')),
        ('odin', service, ('result^ = 0', 'if argument > BOUNDED_USER_ARGUMENT_MAX',
                           'return BOUNDED_USER_ARGUMENT_INVALID',
                           'result^ = argument + BOUNDED_USER_ARGUMENT_INCREMENT',
                           'return BOUNDED_USER_ARGUMENT_OK')),
        ('constants', service, ('BOUNDED_USER_ARGUMENT_MAX :: u64(65535)',
                                'BOUNDED_USER_ARGUMENT_INCREMENT :: u64(1)')),
        ('qword_count', privilege, ('%define FIXED_USER_RESPONSE_QWORDS (FIXED_USER_RESPONSE_SIZE / 8)',)),
        ('construction', section(privilege, 'user_privilege_probe_start:', 'user_privilege_probe_end:'),
         ('mov rax, FIXED_USER_ARGUMENT_OPERAND', 'mov [rdi + 24], rax',
          'mov rcx, FIXED_USER_DATA_SCRATCH_VA', 'mov [rcx], rax', 'int KOZO_PRIVILEGE_RETURN_VECTOR')),
        ('range', section(privilege, 'validate_fixed_user_request:', 'runtime_status_snapshot_fields_are_valid:'),
         ('cmp qword [rel fixed_user_request_shadow + 24], FIXED_USER_ARGUMENT_MAX', 'ja .invalid')),
        ('bridge', section(privilege, 'build_fixed_user_runtime_status_response:', 'validate_fixed_user_response:'),
         ('mov [rel fixed_user_response_shadow + 80], rax',
          'mov rdi, [rel fixed_user_request_shadow + 24]',
          'lea rsi, [rel fixed_user_response_shadow + 88]',
          'call evaluate_bounded_user_argument', 'test eax, eax', 'jnz .failed')),
        ('computed_result', section(privilege, 'validate_fixed_user_response:', 'fixed_user_response_fields_are_valid:'),
         ('call validate_fixed_user_argument_result', 'jnz .invalid',
          'mov rax, [rel fixed_user_response_shadow + 88]',
          'sub rax, FIXED_USER_ARGUMENT_INCREMENT',
          'cmp rax, [rel fixed_user_request_shadow + 24]', 'jne .invalid')),
        ('consumer', section(privilege, 'user_response_consumer_start:', 'user_response_consumer_end:'),
         ('cmp qword [rdi + 80], 0', 'mov rcx, FIXED_USER_DATA_SCRATCH_VA',
          'mov rax, [rcx]', 'cmp rax, FIXED_USER_ARGUMENT_MAX', 'ja .write_record',
          'add rax, FIXED_USER_ARGUMENT_INCREMENT', 'cmp [rdi + 88], rax', 'jne .write_record',
          'xor rax, [rdi + 88]', 'mov [rsi + 32], rax', 'int KOZO_PRIVILEGE_RETURN_VECTOR')),
        ('digest', section(privilege, 'fixed_user_response_digest:', 'clear_fixed_user_response_transaction:'),
         tuple(f'xor rax, [rdi + {offset}]' for offset in range(8, 96, 8))),
        ('readback', section(privilege, 'validate_fixed_user_response_readback:', 'prepare_user_response_resume:'),
         ('mov rax, [rsi + 88]', 'mov [rdi + 88], rax',
          'mov ecx, FIXED_USER_RESPONSE_QWORDS', 'cmp [rdi], rax', 'jne .failed')),
        ('cleanup', section(privilege, 'clear_fixed_user_response_transaction:', 'clear_fixed_user_request_buffers:'),
         ('mov rdi, FIXED_USER_RESPONSE_VA', 'mov ecx, FIXED_USER_RESPONSE_QWORDS', 'rep stosq',
          'lea rdi, [rel fixed_user_response_shadow]', 'mov ecx, FIXED_USER_RESPONSE_QWORDS', 'rep stosq',
          'lea rdi, [rel fixed_user_response_verify]', 'mov ecx, FIXED_USER_RESPONSE_QWORDS', 'rep stosq')),
        ('reuse_cleanup', section(privilege, 'clear_fixed_user_reused_storage:', 'fixed_user_buffers_are_zero:'),
         ('mov rdi, FIXED_USER_DATA_SCRATCH_VA', 'rep stosq',
          'mov rdi, USER_PROBE_STACK_VA', 'rep stosq',
          'call fixed_user_buffers_are_zero', 'mov rdi, FIXED_USER_DATA_SCRATCH_VA',
          'call fixed_qword_span_is_zero')),
    )


def ordered_tokens_present(source, tokens):
    position = 0
    for token in tokens:
        match = source.find(token, position)
        if match < 0:
            return False
        position = match + len(token)
    return True


def section(source, start, end):
    first = source.find(start)
    last = source.find(end, first + len(start))
    return source[first:last] if 0 <= first < last else ''
