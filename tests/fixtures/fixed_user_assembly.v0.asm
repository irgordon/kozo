user_probe_code_start:
user_privilege_probe_start:
    mov ax, cs
    and eax, 3
    cmp eax, 3
    jne user_privilege_probe_failed
    mov rdx, rsp
    mov rax, USER_STACK_SENTINEL
    push rax
    pop rcx
    cmp rcx, rax
    jne user_privilege_probe_failed
    cmp rsp, rdx
    jne user_privilege_probe_failed

    mov rdi, FIXED_USER_REQUEST_VA
    mov dword [rdi], FIXED_USER_REQUEST_VERSION
    mov dword [rdi + 4], FIXED_USER_REQUEST_ID
    mov dword [rdi + 8], FIXED_USER_REQUEST_SIZE
    mov dword [rdi + 12], FIXED_USER_RESPONSE_SIZE
    mov qword [rdi + 16], FIXED_USER_REQUEST_SEQUENCE
    mov rax, FIXED_USER_ARGUMENT_OPERAND
    mov [rdi + 24], rax
    mov rcx, FIXED_USER_DATA_SCRATCH_VA
    mov [rcx], rax
    mov dword [rdi + 32], FIXED_USER_REQUEST_FLAGS
    mov dword [rdi + 36], 0
    cmp [rdi + 24], rax
    jne user_privilege_probe_failed
    push qword USER_RFLAGS
    popfq
    int KOZO_PRIVILEGE_RETURN_VECTOR
user_privilege_probe_after_interrupt:
    ud2

user_privilege_probe_failed:
    mov rdi, FIXED_USER_REQUEST_VA
    mov rax, USER_PROBE_FAILURE_TOKEN
    mov [rdi], rax
    int KOZO_PRIVILEGE_RETURN_VECTOR
    ud2
user_privilege_probe_end:

user_response_consumer_start:
    mov rdi, FIXED_USER_RESPONSE_VA
    mov ax, cs
    and eax, 3
    cmp eax, 3
    jne .cpl_invalid
    mov rdx, rsp
    mov rax, USER_INITIAL_RSP
    cmp rdx, rax
    jne .stack_invalid
    mov rax, USER_STACK_SENTINEL
    push rax
    pop rcx
    cmp rcx, rax
    jne .stack_invalid
    cmp rsp, rdx
    jne .stack_invalid

    mov r8d, 1
    cmp dword [rdi], FIXED_USER_REQUEST_VERSION
    jne .write_record
    mov r8d, 2
    cmp dword [rdi + 4], FIXED_USER_REQUEST_ID
    jne .write_record
    mov r8d, 3
    cmp dword [rdi + 8], PRIVILEGE_TRANSITION_SUCCESS
    jne .write_record
    mov r8d, 4
    cmp dword [rdi + 12], FIXED_USER_RESPONSE_SIZE
    jne .write_record
    mov r8d, 5
    cmp qword [rdi + 16], FIXED_USER_REQUEST_SEQUENCE
    jne .write_record
    mov r8d, 6
    cmp dword [rdi + 24], RUNTIME_STATUS_STAGE
    jne .write_record
    mov r8d, 7
    cmp dword [rdi + 28], 0
    jne .write_record
    mov r8d, 8
    cmp qword [rdi + 32], RUNTIME_STATUS_PROVEN_STAGE_MASK
    jne .write_record
    mov r8d, 9
    cmp qword [rdi + 40], RUNTIME_STATUS_BOOT_MEMORY_SIZE
    jne .write_record
    mov r8d, 10
    cmp qword [rdi + 48], RUNTIME_STATUS_LOOP_LIMIT
    jne .write_record
    mov r8d, 11
    cmp qword [rdi + 56], RUNTIME_STATUS_LOOP_FINAL_COUNT
    jne .write_record
    mov r8d, 12
    cmp qword [rdi + 64], RUNTIME_STATUS_LOOP_FINAL_ACCUMULATOR
    jne .write_record
    mov r8d, 13
    cmp qword [rdi + 72], RUNTIME_STATUS_FEATURE_MASK
    jne .write_record
    mov r8d, 14
    cmp qword [rdi + 80], 0
    jne .write_record
    mov r8d, 15
    mov rcx, FIXED_USER_DATA_SCRATCH_VA
    mov rax, [rcx]
    cmp rax, FIXED_USER_ARGUMENT_MAX
    ja .write_record
    add rax, FIXED_USER_ARGUMENT_INCREMENT
    cmp [rdi + 88], rax
    jne .write_record
    xor r8d, r8d
    jmp .write_record

.cpl_invalid:
    mov r8d, 10
    jmp .write_record
.stack_invalid:
    mov r8d, 11

.write_record:
    mov rsi, FIXED_USER_CONSUMPTION_RECORD_VA
    mov dword [rsi], FIXED_USER_CONSUMPTION_RECORD_VERSION
    mov dword [rsi + 4], FIXED_USER_CONSUMPTION_RECORD_ID
    mov dword [rsi + 8], FIXED_USER_CONSUMPTION_RECORD_SIZE
    mov [rsi + 12], r8d
    mov rax, [rdi + 16]
    mov [rsi + 16], rax
    mov rax, [rdi + 32]
    mov [rsi + 24], rax
    mov rax, [rdi]
    xor rax, [rdi + 8]
    xor rax, [rdi + 16]
    xor rax, [rdi + 24]
    xor rax, [rdi + 32]
    xor rax, [rdi + 40]
    xor rax, [rdi + 48]
    xor rax, [rdi + 56]
    xor rax, [rdi + 64]
    xor rax, [rdi + 72]
    xor rax, [rdi + 80]
    xor rax, [rdi + 88]
    mov [rsi + 32], rax
    mov qword [rsi + 40], 0
    push qword USER_RFLAGS
    popfq
    int KOZO_PRIVILEGE_RETURN_VECTOR
user_response_consumer_interrupt_return:
    ud2
user_response_consumer_end:
    times KOZO_PAGE_SIZE - ($ - user_probe_code_start) db 0x90
user_probe_code_end:
