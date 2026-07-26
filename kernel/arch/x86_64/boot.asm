bits 64

extern kernel_entry
extern runtime_progression_entry
extern initialize_fixed_user_mapping_tables
extern validate_fixed_user_mapping_policy
extern activate_fixed_user_mapping_root
extern run_fixed_user_mapping_survival_probe
global _start
global boot_memory_region
global boot_memory_region_end
global runtime_bootstrap_context
global initialize_cpu_extended_state
global required_cpu_features_available
global configure_extended_state_controls
global verify_extended_state_controls
global initialize_x87_state
global initialize_sse_state
global run_simd_survival_probe
global observed_x87_control_word
global observed_mxcsr
global simd_probe_result
global simd_probe_result_end
global runtime_serial_write_init_marker
global runtime_serial_write_loop_enter_marker
global runtime_serial_write_loop_iter_1_marker
global runtime_serial_write_loop_iter_2_marker
global runtime_serial_write_loop_iter_3_marker
global runtime_serial_write_loop_exit_marker
global runtime_serial_write_capability_dispatch_marker
global runtime_serial_write_status_query_marker
global runtime_serial_write_first_capability_marker
global runtime_serial_write_state_update_enter_marker
global runtime_serial_write_state_update_ok_marker
global runtime_serial_write_second_capability_marker

%define COM1 0x03f8
%define COM1_INTERRUPT_ENABLE 0x03f9
%define COM1_FIFO_CONTROL 0x03fa
%define COM1_LINE_CONTROL 0x03fb
%define COM1_MODEM_CONTROL 0x03fc
%define COM1_LINE_STATUS 0x03fd
%define LINE_CONTROL_DLAB 0x80
%define LINE_CONTROL_8N1 0x03
%define FIFO_ENABLE_CLEAR 0xc7
%define MODEM_READY 0x03
%define TRANSMIT_READY 0x20
%define CPU_REQUIRED_FEATURE_MASK 0x07000001
%define CR0_REQUIRED_SET_MASK 0x22
%define CR0_REQUIRED_CLEAR_MASK 0x0c
%define CR4_REQUIRED_SET_MASK 0x600
%define CR4_OSXSAVE_MASK 0x40000
%define CPU_EXT_STATE_CPUID_UNAVAILABLE 1
%define CPU_EXT_STATE_REQUIRED_FEATURE_MISSING 2
%define CPU_EXT_STATE_CONTROL_CONFIGURATION_FAILED 3
%define CPU_EXT_STATE_X87_INITIALIZATION_FAILED 4
%define CPU_EXT_STATE_SSE_INITIALIZATION_FAILED 5
%define CPU_EXT_STATE_SIMD_PROBE_FAILED 6

%macro INIT_COM1 0
    mov dx, COM1_INTERRUPT_ENABLE
    xor al, al
    out dx, al
    mov dx, COM1_LINE_CONTROL
    mov al, LINE_CONTROL_DLAB
    out dx, al
    mov dx, COM1
    mov al, 3
    out dx, al
    mov dx, COM1_INTERRUPT_ENABLE
    xor al, al
    out dx, al
    mov dx, COM1_LINE_CONTROL
    mov al, LINE_CONTROL_8N1
    out dx, al
    mov dx, COM1_FIFO_CONTROL
    mov al, FIFO_ENABLE_CLEAR
    out dx, al
    mov dx, COM1_MODEM_CONTROL
    mov al, MODEM_READY
    out dx, al
%endmacro

%macro WRITE_COM1_MARKER 2
    lea rsi, [rel %1]
    mov rcx, %2 - %1
    cld
%%marker_loop:
    mov dx, COM1_LINE_STATUS
    in al, dx
    test al, TRANSMIT_READY
    jz %%marker_loop
    lodsb
    mov dx, COM1
    out dx, al
    loop %%marker_loop
%endmacro

section .bss
align 16
boot_stack:
    resb 16384
boot_stack_top:

align 4096
boot_memory_region:
    resb 4096
boot_memory_region_end:

alignb 16
observed_x87_control_word:
    resw 1
alignb 4
observed_mxcsr:
    resd 1
alignb 16
simd_probe_result:
    resb 16
simd_probe_result_end:

section .note.GNU-stack
section .rodata

early_entry_marker:
    db "KOZO_EARLY_0_ENTRY", 13, 10
early_entry_marker_end:

early_serial_init_start_marker:
    db "KOZO_EARLY_1_SERIAL_INIT_START", 13, 10
early_serial_init_start_marker_end:

early_serial_init_ok_marker:
    db "KOZO_EARLY_2_SERIAL_INIT_OK", 13, 10
early_serial_init_ok_marker_end:

boot_smoke_marker:
    db "KOZO_BOOT_SMOKE_OK", 13, 10
boot_smoke_marker_end:

stack_init_marker:
    db "KOZO_STACK_INIT_OK", 13, 10
stack_init_marker_end:

memory_init_marker:
    db "KOZO_MEMORY_INIT_OK", 13, 10
memory_init_marker_end:

cpu_ext_state_init_start_marker:
    db "KOZO_CPU_EXT_STATE_INIT_START", 13, 10
cpu_ext_state_init_start_marker_end:

cpu_ext_state_init_ok_marker:
    db "KOZO_CPU_EXT_STATE_INIT_OK", 13, 10
cpu_ext_state_init_ok_marker_end:

simd_probe_ok_marker:
    db "KOZO_SIMD_PROBE_OK", 13, 10
simd_probe_ok_marker_end:

user_mapping_init_start_marker:
    db "KOZO_USER_MAPPING_INIT_START", 13, 10
user_mapping_init_start_marker_end:

user_mapping_tables_ok_marker:
    db "KOZO_USER_MAPPING_TABLES_OK", 13, 10
user_mapping_tables_ok_marker_end:

user_mapping_permissions_ok_marker:
    db "KOZO_USER_MAPPING_PERMISSIONS_OK", 13, 10
user_mapping_permissions_ok_marker_end:

user_mapping_activate_ok_marker:
    db "KOZO_USER_MAPPING_ACTIVATE_OK", 13, 10
user_mapping_activate_ok_marker_end:

user_mapping_survival_ok_marker:
    db "KOZO_USER_MAPPING_SURVIVAL_OK", 13, 10
user_mapping_survival_ok_marker_end:

runtime_progress_entry_marker:
    db "KOZO_RUNTIME_PROGRESS_ENTRY", 13, 10
runtime_progress_entry_marker_end:

runtime_init_marker:
    db "KOZO_RUNTIME_INIT_OK", 13, 10
runtime_init_marker_end:

runtime_loop_enter_marker:
    db "KOZO_RUNTIME_LOOP_ENTER", 13, 10
runtime_loop_enter_marker_end:

runtime_loop_iter_1_marker:
    db "KOZO_RUNTIME_LOOP_ITER_1", 13, 10
runtime_loop_iter_1_marker_end:

runtime_loop_iter_2_marker:
    db "KOZO_RUNTIME_LOOP_ITER_2", 13, 10
runtime_loop_iter_2_marker_end:

runtime_loop_iter_3_marker:
    db "KOZO_RUNTIME_LOOP_ITER_3", 13, 10
runtime_loop_iter_3_marker_end:

runtime_loop_exit_marker:
    db "KOZO_RUNTIME_LOOP_EXIT_OK", 13, 10
runtime_loop_exit_marker_end:

capability_dispatch_marker:
    db "KOZO_CAPABILITY_DISPATCH_ENTER", 13, 10
capability_dispatch_marker_end:

runtime_status_query_marker:
    db "KOZO_RUNTIME_STATUS_QUERY_OK", 13, 10
runtime_status_query_marker_end:

first_capability_marker:
    db "KOZO_FIRST_CAPABILITY_OK", 13, 10
first_capability_marker_end:

runtime_state_update_enter_marker:
    db "KOZO_RUNTIME_STATE_UPDATE_ENTER", 13, 10
runtime_state_update_enter_marker_end:

runtime_state_update_ok_marker:
    db "KOZO_RUNTIME_STATE_UPDATE_OK", 13, 10
runtime_state_update_ok_marker_end:

second_capability_marker:
    db "KOZO_SECOND_CAPABILITY_OK", 13, 10
second_capability_marker_end:

runtime_return_marker:
    db "KOZO_RUNTIME_RETURN_OK", 13, 10
runtime_return_marker_end:

align 16
default_mxcsr:
    dd 0x00001f80

align 16
simd_probe_input:
    dq 0x0011223344556677
    dq 0x8899aabbccddeeff

align 16
simd_probe_mask:
    dq 0xffff0000ffff0000
    dq 0x0f0f0f0f0f0f0f0f

section .data
align 8
runtime_bootstrap_context:
    dq 1
    dq 64
    dq boot_stack
    dq boot_stack_top
    dq boot_memory_region
    dq boot_memory_region_end
    dq 0
    dq 0

section .text

_start:
    INIT_COM1
    WRITE_COM1_MARKER early_entry_marker, early_entry_marker_end
    WRITE_COM1_MARKER early_serial_init_start_marker, early_serial_init_start_marker_end
    INIT_COM1
    WRITE_COM1_MARKER early_serial_init_ok_marker, early_serial_init_ok_marker_end
    WRITE_COM1_MARKER boot_smoke_marker, boot_smoke_marker_end
    lea rsp, [rel boot_stack_top]
    mov rax, 0x4b4f5a4f5354414b
    push rax
    pop rax
    WRITE_COM1_MARKER stack_init_marker, stack_init_marker_end
    ; Terminal evidence path clobbers rax, rcx, rdi, rdx, and r8 before halting.
    cld
    lea rdi, [rel boot_memory_region]
    xor eax, eax
    mov ecx, 512
    rep stosq
    cli
    cmp qword [rel boot_memory_region], 0
    jne .halt
    mov rax, 0x4b4f5a4f4d454d31
    mov qword [rel boot_memory_region], rax
    mov rdx, qword [rel boot_memory_region]
    cmp rdx, rax
    sete r8b
    mov qword [rel boot_memory_region], 0
    test r8b, r8b
    jz .halt
    cmp qword [rel boot_memory_region], 0
    jne .halt
    WRITE_COM1_MARKER memory_init_marker, memory_init_marker_end
    WRITE_COM1_MARKER cpu_ext_state_init_start_marker, cpu_ext_state_init_start_marker_end
    call initialize_cpu_extended_state
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER cpu_ext_state_init_ok_marker, cpu_ext_state_init_ok_marker_end
    call run_simd_survival_probe
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER simd_probe_ok_marker, simd_probe_ok_marker_end
    WRITE_COM1_MARKER user_mapping_init_start_marker, user_mapping_init_start_marker_end
    call initialize_fixed_user_mapping_tables
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER user_mapping_tables_ok_marker, user_mapping_tables_ok_marker_end
    call validate_fixed_user_mapping_policy
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER user_mapping_permissions_ok_marker, user_mapping_permissions_ok_marker_end
    call activate_fixed_user_mapping_root
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER user_mapping_activate_ok_marker, user_mapping_activate_ok_marker_end
    call run_fixed_user_mapping_survival_probe
    test eax, eax
    jnz .halt
    WRITE_COM1_MARKER user_mapping_survival_ok_marker, user_mapping_survival_ok_marker_end
    test rsp, 0x0f
    jnz .halt
    lea rdi, [rel runtime_bootstrap_context]
    WRITE_COM1_MARKER runtime_progress_entry_marker, runtime_progress_entry_marker_end
    call runtime_progression_entry
    cmp eax, 0
    jne .halt
    WRITE_COM1_MARKER runtime_return_marker, runtime_return_marker_end
    cli

.halt:
    hlt
    jmp .halt

; Input: none. Output: eax is an exact CPU_EXT_STATE status.
; Preserves rbx; clobbers other caller-saved registers and CPU control state.
initialize_cpu_extended_state:
    push rbx
    call required_cpu_features_available
    test eax, eax
    jnz .done
    call configure_extended_state_controls
    call verify_extended_state_controls
    test eax, eax
    jnz .done
    call initialize_x87_state
    test eax, eax
    jnz .done
    call initialize_sse_state
.done:
    pop rbx
    ret

; Input: none. Output: eax is success or a CPUID capability status.
; Clobbers rax-rdx; rbx is preserved by the caller.
required_cpu_features_available:
    xor eax, eax
    cpuid
    cmp eax, 1
    jb .cpuid_unavailable
    mov eax, 1
    cpuid
    and edx, CPU_REQUIRED_FEATURE_MASK
    cmp edx, CPU_REQUIRED_FEATURE_MASK
    jne .required_feature_missing
    xor eax, eax
    ret
.cpuid_unavailable:
    mov eax, CPU_EXT_STATE_CPUID_UNAVAILABLE
    ret
.required_feature_missing:
    mov eax, CPU_EXT_STATE_REQUIRED_FEATURE_MISSING
    ret

; Input: none. Output: eax is success.
; Preserves unrelated CR0/CR4 policy and clobbers rax.
configure_extended_state_controls:
    mov rax, cr0
    or rax, CR0_REQUIRED_SET_MASK
    and rax, ~CR0_REQUIRED_CLEAR_MASK
    mov cr0, rax
    mov rax, cr4
    or rax, CR4_REQUIRED_SET_MASK
    and rax, ~CR4_OSXSAVE_MASK
    mov cr4, rax
    xor eax, eax
    ret

; Input: configured CR0/CR4. Output: eax is success or configuration failure.
; Clobbers rax and rdx.
verify_extended_state_controls:
    mov rax, cr0
    mov rdx, rax
    and rax, CR0_REQUIRED_SET_MASK
    cmp rax, CR0_REQUIRED_SET_MASK
    jne .control_failure
    test rdx, CR0_REQUIRED_CLEAR_MASK
    jnz .control_failure
    mov rax, cr4
    mov rdx, rax
    and rax, CR4_REQUIRED_SET_MASK
    cmp rax, CR4_REQUIRED_SET_MASK
    jne .control_failure
    test rdx, CR4_OSXSAVE_MASK
    jnz .control_failure
    xor eax, eax
    ret
.control_failure:
    mov eax, CPU_EXT_STATE_CONTROL_CONFIGURATION_FAILED
    ret

; Input: configured x87 control state. Output: eax is success or x87 failure.
; Touches only the bounded x87 observation word.
initialize_x87_state:
    fninit
    fnstcw [rel observed_x87_control_word]
    cmp word [rel observed_x87_control_word], 0x037f
    jne .x87_failure
    xor eax, eax
    ret
.x87_failure:
    mov eax, CPU_EXT_STATE_X87_INITIALIZATION_FAILED
    ret

; Input: configured SSE control state. Output: eax is success or SSE failure.
; Touches only the bounded MXCSR observation word.
initialize_sse_state:
    ldmxcsr [rel default_mxcsr]
    stmxcsr [rel observed_mxcsr]
    cmp dword [rel observed_mxcsr], 0x00001f80
    jne .sse_failure
    xor eax, eax
    ret
.sse_failure:
    mov eax, CPU_EXT_STATE_SSE_INITIALIZATION_FAILED
    ret

; Input: initialized SSE2 state. Output: eax is success or probe failure.
; Touches 16 bounded bytes and xmm0, both cleared before return.
run_simd_survival_probe:
    movdqa xmm0, [rel simd_probe_input]
    pxor xmm0, [rel simd_probe_mask]
    movdqa [rel simd_probe_result], xmm0
    mov rax, 0xffee2233bbaa6677
    cmp qword [rel simd_probe_result], rax
    jne .probe_failure
    mov rax, 0x8796a5b4c3d2e1f0
    cmp qword [rel simd_probe_result + 8], rax
    jne .probe_failure
    mov qword [rel simd_probe_result], 0
    mov qword [rel simd_probe_result + 8], 0
    pxor xmm0, xmm0
    xor eax, eax
    ret
.probe_failure:
    mov qword [rel simd_probe_result], 0
    mov qword [rel simd_probe_result + 8], 0
    pxor xmm0, xmm0
    mov eax, CPU_EXT_STATE_SIMD_PROBE_FAILED
    ret

runtime_serial_write_init_marker:
    WRITE_COM1_MARKER runtime_init_marker, runtime_init_marker_end
    ret

runtime_serial_write_loop_enter_marker:
    WRITE_COM1_MARKER runtime_loop_enter_marker, runtime_loop_enter_marker_end
    ret

runtime_serial_write_loop_iter_1_marker:
    WRITE_COM1_MARKER runtime_loop_iter_1_marker, runtime_loop_iter_1_marker_end
    ret

runtime_serial_write_loop_iter_2_marker:
    WRITE_COM1_MARKER runtime_loop_iter_2_marker, runtime_loop_iter_2_marker_end
    ret

runtime_serial_write_loop_iter_3_marker:
    WRITE_COM1_MARKER runtime_loop_iter_3_marker, runtime_loop_iter_3_marker_end
    ret

runtime_serial_write_loop_exit_marker:
    WRITE_COM1_MARKER runtime_loop_exit_marker, runtime_loop_exit_marker_end
    ret

runtime_serial_write_capability_dispatch_marker:
    WRITE_COM1_MARKER capability_dispatch_marker, capability_dispatch_marker_end
    ret

runtime_serial_write_status_query_marker:
    WRITE_COM1_MARKER runtime_status_query_marker, runtime_status_query_marker_end
    ret

runtime_serial_write_first_capability_marker:
    WRITE_COM1_MARKER first_capability_marker, first_capability_marker_end
    ret

runtime_serial_write_state_update_enter_marker:
    WRITE_COM1_MARKER runtime_state_update_enter_marker, runtime_state_update_enter_marker_end
    ret

runtime_serial_write_state_update_ok_marker:
    WRITE_COM1_MARKER runtime_state_update_ok_marker, runtime_state_update_ok_marker_end
    ret

runtime_serial_write_second_capability_marker:
    WRITE_COM1_MARKER second_capability_marker, second_capability_marker_end
    ret
