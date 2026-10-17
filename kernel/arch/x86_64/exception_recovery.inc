%define USER_EXCEPTION_RFLAGS 0x10002
%define USER_EXCEPTION_RECORD_SIZE 64
%define USER_EXCEPTION_SELECTOR (FIXED_USER_DATA_SCRATCH_VA + 8)

extern __kozo_authorized_ud2_rip
extern runtime_bootstrap_context
extern governed_kernel_pt
extern governed_page_table_root_physical
global bounded_user_exception_handler
global bounded_user_exception_record
global bounded_user_exception_record_end
global observe_bounded_user_exception
global bounded_user_exception_is_complete

section .bss
alignb 8
bounded_user_exception_record: resb USER_EXCEPTION_RECORD_SIZE
bounded_user_exception_record_end:

section .text
bounded_user_exception_handler:
    cli
    cld
    mov ax, KERNEL_DATA_SELECTOR
    mov ss, ax
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov r15, rsp
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 1
    sub r15, 8
%endif
%endif
    mov ebx, 1
    lea rax, [rel privilege_return_stack_top - 40]
    cmp r15, rax
    jne reject_user_exception
    sub rsp, 8
%ifdef KOZO_FAULT_SESSION
    call mutate_user_exception_fixture_state
%endif
    mov ebx, 2
    mov rax, [r15 + 8]
    and eax, 3
    cmp eax, 3
    jne reject_user_exception
    mov ebx, 3
    cmp qword [r15 + 8], USER_CODE_SELECTOR
    jne reject_user_exception
    mov ebx, 4
    cmp qword [r15 + 32], USER_DATA_SELECTOR
    jne reject_user_exception
    mov ebx, 5
    cmp qword [r15 + 16], USER_EXCEPTION_RFLAGS
    jne reject_user_exception
    mov rax, __kozo_authorized_ud2_rip
    test rax, rax
    jz .site_disabled
    mov ebx, 6
    cmp [r15], rax
    jne reject_user_exception
    mov rdx, USER_PROBE_CODE_VA
    sub rax, rdx
    cmp rax, KOZO_PAGE_SIZE - 2
    ja reject_user_exception
    mov r12, rax
    mov ebx, 7
    mov rdi, USER_PROBE_CODE_VA
    call walk_page_mapping
    mov r13, rax
    cmp rdx, PTE_PRESENT | PTE_USER
    jne reject_user_exception
    lea rdi, [rel user_probe_code_start]
    call physical_for_kernel_virtual
    cmp r13, rax
    jne reject_user_exception
    ; The higher-half backing symbol is intentionally unmapped. Validate its
    ; physical translation before reading through the existing fixed RX alias.
    mov rax, USER_PROBE_CODE_VA
    add rax, r12
    cmp word [rax], 0x0b0f
    jne reject_user_exception
    mov ebx, 8
%ifdef USER_EXCEPTION_EXPECTED_RSP
    mov rax, USER_EXCEPTION_EXPECTED_RSP
    cmp [r15 + 24], rax
    jne reject_user_exception
%else
    jmp .site_disabled
%endif
    mov ebx, 9
    cmp qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING
    jne reject_user_exception
    mov ebx, 10
    cmp dword [rel fixed_user_context], FIXED_USER_CONTEXT_FORMAT_VERSION
    jne reject_user_exception
    cmp dword [rel fixed_user_context + 4], FIXED_USER_CONTEXT_SIZE
    jne reject_user_exception
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_SESSION == 1
    mov rax, FIXED_USER_CONTEXT_OPAQUE_IDENTITY
%else
    mov rax, FIXED_USER_CONTEXT_SECOND_OPAQUE_IDENTITY
%endif
    cmp [rel fixed_user_context + FIXED_USER_CONTEXT_OPAQUE_IDENTITY_OFFSET], rax
    jne reject_user_exception
%endif
    cmp dword [rel fixed_user_context + FIXED_USER_CONTEXT_LIFECYCLE_OFFSET], FIXED_USER_CONTEXT_ACTIVE
    jne reject_user_exception
    call validate_fixed_user_context_bindings
    test eax, eax
    jnz reject_user_exception
    call validate_fixed_user_context_reserved_state
    test eax, eax
    jnz reject_user_exception
    mov ebx, 11
%ifdef KOZO_FAULT_SESSION
    cmp dword [rel repeated_user_session_coordinator + REPEATED_USER_SESSION_ACTIVE_ORDINAL_OFFSET], KOZO_FAULT_SESSION
    jne reject_user_exception
%else
    jmp .site_disabled
%endif
    mov ebx, 12
    cmp dword [rel fixed_user_context + FIXED_USER_CONTEXT_TRANSITION_COUNT_OFFSET], 0
    jne reject_user_exception
    mov ebx, 13
    call validate_user_exception_continuation
    test eax, eax
    jnz reject_user_exception
    mov ebx, 14
    call user_exception_record_is_empty
    test eax, eax
    jnz reject_user_exception
    call record_authorized_user_exception
    test eax, eax
    jnz reject_user_exception
    mov rsp, [rel saved_odin_return_stack]
    mov qword [rel saved_odin_return_stack], 0
    mov eax, USER_EXCEPTION_STATUS
    ret
.site_disabled:
    mov ebx, 15
    jmp reject_user_exception

finish_authorized_user_exception:
    sub rsp, 8
    mov edi, 1
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 27
    mov edi, 3
%endif
%endif
    call advance_user_exception_stage
    test eax, eax
    jnz .failed
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 30
    call observe_bounded_user_exception
    jmp .failed
%elif KOZO_FAULT_MODE == 31
    mov dword [rel bounded_user_exception_record + 8], 2
    mov edi, 1
    call advance_user_exception_stage
    test eax, eax
    jnz .failed
%endif
%endif
    mov edi, FIXED_USER_CONTEXT_FAILURE_INVALID_RETURN_STATE
    call fail_and_clear_fixed_user_execution_context
    test eax, eax
    jnz .failed
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 26
    mov edi, FIXED_USER_CONTEXT_FAILURE_INVALID_RETURN_STATE
    call fail_and_clear_fixed_user_execution_context
    test eax, eax
    jnz .failed
%endif
%endif
    mov edi, 2
    call advance_user_exception_stage
    test eax, eax
    jnz .failed
    call clear_fixed_user_request_buffers
    test eax, eax
    jnz .failed
    mov qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING
    mov qword [rel privilege_probe_state], 0
    mov qword [rel fixed_user_request_success_state], 0
    call reset_fixed_user_context_result
    test eax, eax
    jnz .failed
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 22
    mov rdi, FIXED_USER_DATA_SCRATCH_VA
    mov byte [rdi], 1
%endif
%endif
    call user_exception_cleanup_is_valid
    test eax, eax
    jnz .failed
    mov edi, 3
    call advance_user_exception_stage
    test eax, eax
    jnz .failed
    mov eax, USER_EXCEPTION_STATUS
    add rsp, 8
    ret
.failed:
    xor ebx, ebx
    jmp reject_user_exception

observe_bounded_user_exception:
    sub rsp, 8
    call user_exception_cleanup_is_valid
    test eax, eax
    jnz .done
    mov edi, 4
    call advance_user_exception_stage
    test eax, eax
    jnz .done
    lea rsi, [rel user_exception_recovered_text]
    mov ecx, user_exception_recovered_text_end - user_exception_recovered_text
    call write_user_exception_text
    lea rdi, [rel bounded_user_exception_record]
    mov r8d, USER_EXCEPTION_RECORD_SIZE / 4
.record_word:
    mov eax, [rdi]
    lea rsi, [rel user_exception_record_text]
    mov ecx, user_exception_record_text_end - user_exception_record_text
    call write_user_exception_value
    add rdi, 4
    dec r8d
    jnz .record_word
    xor eax, eax
.done:
    test eax, eax
    jnz .failed
    add rsp, 8
    ret
.failed:
    xor ebx, ebx
    jmp reject_user_exception

bounded_user_exception_is_complete:
    cmp dword [rel bounded_user_exception_record + 8], 5
    jne user_exception_invalid
    jmp user_exception_cleanup_is_valid

user_exception_cleanup_is_valid:
    call validate_fixed_user_execution_context_cleared
    test eax, eax
    jnz .done
    call fixed_user_context_result_is_initial
    test eax, eax
    jnz .done
    call fixed_user_session_storage_is_zero
    test eax, eax
    jnz .done
    cmp qword [rel fixed_user_transaction_phase], FIXED_USER_PHASE_REQUEST_PENDING
    jne user_exception_invalid
    cmp qword [rel saved_odin_return_stack], 0
    jne user_exception_invalid
    xor eax, eax
.done:
    ret

validate_user_exception_continuation:
    mov rax, [rel saved_odin_return_stack]
    test rax, 7
    jnz user_exception_invalid
    cmp rax, [rel runtime_bootstrap_context + 16]
    jbe user_exception_invalid
    mov rdx, [rel runtime_bootstrap_context + 24]
    sub rdx, 64
    cmp rax, rdx
    ja user_exception_invalid
    lea rdx, [rel execute_fixed_user_runtime_status_transaction.exception_wrapper_return]
    cmp [rax], rdx
    jne user_exception_invalid
    xor eax, eax
    ret

initialize_bounded_user_exception_record:
    lea rdi, [rel bounded_user_exception_record]
    xor eax, eax
    mov ecx, USER_EXCEPTION_RECORD_SIZE / 8
    rep stosq
    mov dword [rel bounded_user_exception_record], 1
    mov dword [rel bounded_user_exception_record + 4], USER_EXCEPTION_RECORD_SIZE
    ret

user_exception_record_is_empty:
    cmp dword [rel bounded_user_exception_record], 1
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 4], USER_EXCEPTION_RECORD_SIZE
    jne user_exception_invalid
    lea rdi, [rel bounded_user_exception_record + 8]
    mov ecx, 7
    jmp fixed_qword_span_is_zero

record_authorized_user_exception:
    sub rsp, 8
    mov rax, [r15 + 16]
    lea rsi, [rel user_exception_flags_text]
    mov ecx, user_exception_flags_text_end - user_exception_flags_text
    call write_user_exception_value
    add rsp, 8
    mov dword [rel bounded_user_exception_record + 12], USER_EXCEPTION_STATUS
    mov dword [rel bounded_user_exception_record + 16], 6
    mov eax, [rel repeated_user_session_coordinator + REPEATED_USER_SESSION_ACTIVE_ORDINAL_OFFSET]
    mov [rel bounded_user_exception_record + 20], eax
    mov dword [rel bounded_user_exception_record + 32], 1
    mov dword [rel bounded_user_exception_record + 40], 0x7fff
    xor edi, edi
    jmp advance_user_exception_stage

advance_user_exception_stage:
    cmp dword [rel bounded_user_exception_record], 1
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 4], USER_EXCEPTION_RECORD_SIZE
    jne user_exception_invalid
    cmp edi, 4
    ja user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 12], USER_EXCEPTION_STATUS
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 16], 6
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 20], 1
    jb user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 20], 2
    ja user_exception_invalid
    cmp qword [rel bounded_user_exception_record + 24], 0
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 32], 1
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 36], 0
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 40], 0x7fff
    jne user_exception_invalid
    cmp [rel bounded_user_exception_record + 8], edi
    jne user_exception_invalid
    cmp dword [rel bounded_user_exception_record + 44], 0
    jne user_exception_invalid
    cmp qword [rel bounded_user_exception_record + 48], 0
    jne user_exception_invalid
    cmp qword [rel bounded_user_exception_record + 56], 0
    jne user_exception_invalid
    inc edi
    mov [rel bounded_user_exception_record + 8], edi
%ifdef KOZO_FAULT_SESSION
%if KOZO_FAULT_MODE == 28
    inc dword [rel bounded_user_exception_record + 8]
%endif
%endif
    cmp [rel bounded_user_exception_record + 8], edi
    jne user_exception_invalid
    mov eax, edi
    lea rsi, [rel user_exception_stage_text]
    mov ecx, user_exception_stage_text_end - user_exception_stage_text
    sub rsp, 8
    call write_user_exception_value
    add rsp, 8
    xor eax, eax
    ret

user_exception_invalid:
    mov eax, 1
    ret

%ifdef KOZO_FAULT_SESSION
mutate_user_exception_fixture_state:
%if KOZO_FAULT_MODE == 2
    and qword [r15 + 8], ~3
%elif KOZO_FAULT_MODE == 3
    mov qword [r15 + 8], 0x2b
%elif KOZO_FAULT_MODE == 4
    mov qword [r15 + 32], 0x13
%elif KOZO_FAULT_MODE == 5
    xor qword [r15 + 16], 1
%elif KOZO_FAULT_MODE == 10
    mov dword [rel fixed_user_context + FIXED_USER_CONTEXT_LIFECYCLE_OFFSET], FIXED_USER_CONTEXT_READY
%elif KOZO_FAULT_MODE == 11
    mov dword [rel repeated_user_session_coordinator + REPEATED_USER_SESSION_ACTIVE_ORDINAL_OFFSET], 3
%elif KOZO_FAULT_MODE == 12
    mov dword [rel fixed_user_context + FIXED_USER_CONTEXT_TRANSITION_COUNT_OFFSET], 1
%elif KOZO_FAULT_MODE == 13
    mov qword [rel saved_odin_return_stack], 0
%elif KOZO_FAULT_MODE == 14
    mov dword [rel bounded_user_exception_record + 8], 1
%elif KOZO_FAULT_MODE == 16
    lea rdx, [rel fixed_user_context]
    shr rdx, 12
    and edx, 511
    lea rdi, [rel governed_kernel_pt]
    and qword [rdi + rdx * 8], ~PTE_PRESENT
    lea rax, [rel fixed_user_context]
    invlpg [rax]
    mov ebx, 1
    jmp reject_user_exception
%endif
    ret

select_user_exception_fixture:
    mov eax, [rel repeated_user_session_coordinator + REPEATED_USER_SESSION_ACTIVE_ORDINAL_OFFSET]
    cmp eax, 1
    jb user_exception_invalid
    cmp eax, 2
    ja user_exception_invalid
    mov rdi, USER_EXCEPTION_SELECTOR
%if KOZO_FAULT_MODE == 25
    mov byte [rdi], 1
%endif
    cmp byte [rdi], 0
    jne user_exception_invalid
    cmp eax, KOZO_FAULT_SESSION
    jne .unselected
%if KOZO_FAULT_MODE == 9
    mov byte [rdi], 2
    cmp byte [rdi], 2
%else
    mov byte [rdi], 1
    cmp byte [rdi], 1
%endif
    jne user_exception_invalid
%if KOZO_FAULT_MODE == 24
    mov byte [rdi], 255
    cmp byte [rdi], 1
    jne user_exception_invalid
%endif
.unselected:
%if KOZO_FAULT_MODE == 18
    lea rsp, [rel privilege_return_stack_top]
    ud2
%elif KOZO_FAULT_MODE == 21
    and byte [rel governed_idt + 13 * 16 + 5], 0x7f
%endif
    xor eax, eax
    ret
%endif

write_user_exception_text:
    mov dx, 0x3f8
.character:
    lodsb
    out dx, al
    loop .character
    ret

write_user_exception_value:
    push rbx
    mov rbx, rax
    call write_user_exception_text
    mov ecx, 16
    lea rsi, [rel user_boundary_hex_digits]
.digit:
    rol rbx, 4
    mov eax, ebx
    and eax, 15
    mov al, [rsi + rax]
    out dx, al
    loop .digit
    mov al, 13
    out dx, al
    mov al, 10
    out dx, al
    pop rbx
    ret

; Never read a saved user address or use a saved continuation on rejection.
reject_user_exception:
    cli
    cld
    mov rax, cr3
    cmp rax, [rel governed_page_table_root_physical]
    jne user_exception_emergency_halt
    lea rdx, [rel fixed_user_context]
    shr rdx, 12
    and edx, 511
    lea rdi, [rel governed_kernel_pt]
    mov rax, [rdi + rdx * 8]
    mov rdx, PTE_NX | PTE_PRESENT | PTE_WRITABLE | PTE_USER
    and rax, rdx
    and rdx, ~PTE_USER
    cmp rax, rdx
    jne user_exception_emergency_halt
    lea rdi, [rel fixed_user_context]
    xor eax, eax
    mov ecx, FIXED_USER_CONTEXT_SIZE / 8
    rep stosq
    mov dword [rel fixed_user_context], FIXED_USER_CONTEXT_FORMAT_VERSION
    mov dword [rel fixed_user_context + 4], FIXED_USER_CONTEXT_SIZE
    mov dword [rel fixed_user_context + FIXED_USER_CONTEXT_LIFECYCLE_OFFSET], FIXED_USER_CONTEXT_CLEARED
    cmp dword [rel fixed_user_context], FIXED_USER_CONTEXT_FORMAT_VERSION
    jne user_exception_emergency_halt
    cmp dword [rel fixed_user_context + 4], FIXED_USER_CONTEXT_SIZE
    jne user_exception_emergency_halt
    cmp dword [rel fixed_user_context + 16], FIXED_USER_CONTEXT_CLEARED
    jne user_exception_emergency_halt
    cmp qword [rel fixed_user_context + 8], 0
    jne user_exception_emergency_halt
    cmp dword [rel fixed_user_context + 20], 0
    jne user_exception_emergency_halt
    lea rdi, [rel fixed_user_context + 24]
    mov ecx, (FIXED_USER_CONTEXT_SIZE - 24) / 8
.readback:
    cmp qword [rdi], 0
    jne user_exception_emergency_halt
    add rdi, 8
    loop .readback
    test ebx, ebx
    jz boot_terminal_halt
    lea rsi, [rel user_exception_reject_text]
    mov ecx, user_exception_reject_text_end - user_exception_reject_text
    mov dx, 0x3f8
.diagnostic:
    lodsb
    out dx, al
    loop .diagnostic
    mov eax, ebx
    xor edx, edx
    mov ecx, 10
    div ecx
    mov ecx, edx
    mov dx, 0x3f8
    add al, '0'
    out dx, al
    mov eax, ecx
    add al, '0'
    out dx, al
    mov al, 13
    out dx, al
    mov al, 10
    out dx, al
    jmp boot_terminal_halt

user_exception_emergency_halt:
    cli
    jmp boot_terminal_halt

section .rodata
user_exception_reject_text: db 'USER_EXCEPTION_REJECT='
user_exception_reject_text_end:
user_exception_recovered_text: db 'USER_EXCEPTION_RECOVERED=06', 13, 10
user_exception_recovered_text_end:
user_exception_flags_text: db 'USER_EXCEPTION_SAVED_RFLAGS='
user_exception_flags_text_end:
user_exception_stage_text: db 'USER_EXCEPTION_STAGE='
user_exception_stage_text_end:
user_exception_record_text: db 'USER_EXCEPTION_RECORD_WORD='
user_exception_record_text_end:
section .text
