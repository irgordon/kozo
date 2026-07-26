bits 64

%include "kernel/arch/x86_64/runtime_layout.inc"

global initialize_privilege_transition
global enter_bounded_ring3_probe
global governed_gdt
global governed_gdt_end
global governed_tss
global governed_tss_end
global governed_idt
global governed_idt_end
global privilege_return_stack
global privilege_return_stack_top
global double_fault_stack
global double_fault_stack_top
global privilege_probe_state
global user_probe_code_start
global user_probe_code_end
global user_privilege_probe_start
global user_privilege_probe_end
global privilege_return_handler
global privilege_ring0_continuation
global observed_governed_gdtr
global observed_governed_idtr
global observed_task_register

extern walk_page_mapping
extern runtime_serial_write_ring3_enter_marker
extern runtime_serial_write_ring3_probe_marker
extern boot_terminal_halt

%define PAGE_QWORDS (KOZO_PAGE_SIZE / 8)
%define GDT_ENTRY_COUNT 7
%define GDT_SIZE (GDT_ENTRY_COUNT * 8)
%define GDT_LIMIT (GDT_SIZE - 1)
%define TSS_SIZE 104
%define TSS_LIMIT (TSS_SIZE - 1)
%define IDT_ENTRY_COUNT 256
%define IDT_SIZE (IDT_ENTRY_COUNT * 16)
%define IDT_LIMIT (IDT_SIZE - 1)

%define PTE_PRESENT 0x001
%define PTE_WRITABLE 0x002
%define PTE_USER 0x004
%define PTE_NX 0x8000000000000000

%define KERNEL_CODE_DESCRIPTOR 0x00af9b000000ffff
%define KERNEL_DATA_DESCRIPTOR 0x00cf93000000ffff
%define USER_DATA_DESCRIPTOR 0x00cff3000000ffff
%define USER_CODE_DESCRIPTOR 0x00affb000000ffff
%define TSS_AVAILABLE_ACCESS 0x89
%define TSS_BUSY_ACCESS 0x8b

%define INTERRUPT_GATE_DPL0 0x8e
%define INTERRUPT_GATE_DPL3 0xee
%define DOUBLE_FAULT_IST_INDEX 1

%define USER_INITIAL_RSP (USER_PROBE_STACK_TOP_VA - 16)
%define USER_RFLAGS 0x2
%define USER_STACK_SENTINEL 0x4b4f5a4f55534552
%define USER_PROBE_TOKEN 0x4b4f5a4f50524956
%define USER_PROBE_FAILURE_TOKEN 0x4641494c50524956
%define PRIVILEGE_PROBE_SUCCESS_STATE 0x4b4f5a4f52335230

%define PRIVILEGE_TRANSITION_SUCCESS 0
%define PRIVILEGE_GDT_INVALID 1
%define PRIVILEGE_TSS_INVALID 2
%define PRIVILEGE_IDT_INVALID 3
%define PRIVILEGE_USER_ENTRY_INVALID 4
%define PRIVILEGE_USER_STACK_INVALID 5
%define PRIVILEGE_RETURN_FRAME_INVALID 6
%define PRIVILEGE_USER_PROBE_FAILED 7
%define PRIVILEGE_RING0_CONTINUATION_FAILED 8

section .user_probe_code progbits alloc exec nowrite align=4096
align 4096
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

    mov rdi, USER_PROBE_DATA_VA
    mov rax, USER_PROBE_TOKEN
    mov [rdi], rax
    cmp [rdi], rax
    jne user_privilege_probe_failed
    push qword USER_RFLAGS
    popfq
    int KOZO_PRIVILEGE_RETURN_VECTOR
user_privilege_probe_after_interrupt:
    ud2

user_privilege_probe_failed:
    mov rdi, USER_PROBE_DATA_VA
    mov rax, USER_PROBE_FAILURE_TOKEN
    mov [rdi], rax
    int KOZO_PRIVILEGE_RETURN_VECTOR
    ud2
user_privilege_probe_end:
    times KOZO_PAGE_SIZE - ($ - user_probe_code_start) db 0x90
user_probe_code_end:

section .bss
alignb 16
governed_gdt:
    resb GDT_SIZE
governed_gdt_end:

alignb 16
governed_tss:
    resb TSS_SIZE
governed_tss_end:

alignb 16
governed_gdtr:
    resb 10
observed_governed_gdtr:
    resb 10

alignb 4096
governed_idt:
    resb IDT_SIZE
governed_idt_end:

alignb 16
governed_idtr:
    resb 10
observed_governed_idtr:
    resb 10

alignb 4096
privilege_return_stack:
    resb KOZO_PAGE_SIZE
privilege_return_stack_top:

alignb 4096
double_fault_stack:
    resb KOZO_PAGE_SIZE
double_fault_stack_top:

alignb 8
privilege_probe_state:
    resq 1
saved_kernel_continuation_rsp:
    resq 1
observed_task_register:
    resw 1

section .note.GNU-stack
section .text

; Coordinates one fixed descriptor setup. Returns one exact PRIVILEGE status.
initialize_privilege_transition:
    call clear_privilege_transition_storage
    call initialize_governed_tss
    call initialize_governed_gdt
    test eax, eax
    jnz .done
    call load_governed_tss
    test eax, eax
    jnz .done
    call initialize_governed_idt
    test eax, eax
    jnz .done
    call validate_privilege_transition_tables
    test eax, eax
    jnz .done
    call validate_user_probe_entry
.done:
    ret

; Clears fixed writable descriptor, stack, and probe state.
clear_privilege_transition_storage:
    cld
    lea rdi, [rel governed_gdt]
    xor eax, eax
    mov ecx, GDT_SIZE / 8
    rep stosq
    lea rdi, [rel governed_tss]
    mov ecx, TSS_SIZE / 8
    rep stosq
    lea rdi, [rel governed_idt]
    mov ecx, IDT_SIZE / 8
    rep stosq
    lea rdi, [rel privilege_return_stack]
    mov ecx, PAGE_QWORDS
    rep stosq
    lea rdi, [rel double_fault_stack]
    mov ecx, PAGE_QWORDS
    rep stosq
    mov qword [rel privilege_probe_state], 0
    mov qword [rel saved_kernel_continuation_rsp], 0
    mov word [rel observed_task_register], 0
    ret

; Populates only RSP0, IST1, and the disabled I/O bitmap offset.
initialize_governed_tss:
    lea rax, [rel privilege_return_stack_top]
    mov [rel governed_tss + 4], rax
    lea rax, [rel double_fault_stack_top]
    mov [rel governed_tss + 36], rax
    mov word [rel governed_tss + 102], TSS_SIZE
    ret

; Builds and loads the fixed GDT, then reloads all governed selectors.
initialize_governed_gdt:
    mov rax, KERNEL_CODE_DESCRIPTOR
    mov [rel governed_gdt + 8], rax
    mov rax, KERNEL_DATA_DESCRIPTOR
    mov [rel governed_gdt + 16], rax
    mov rax, USER_DATA_DESCRIPTOR
    mov [rel governed_gdt + 24], rax
    mov rax, USER_CODE_DESCRIPTOR
    mov [rel governed_gdt + 32], rax
    call populate_tss_descriptor

    mov word [rel governed_gdtr], GDT_LIMIT
    lea rax, [rel governed_gdt]
    mov [rel governed_gdtr + 2], rax
    lgdt [rel governed_gdtr]
    push qword KERNEL_CODE_SELECTOR
    lea rax, [rel .kernel_code_reloaded]
    push rax
    retfq
.kernel_code_reloaded:
    mov ax, KERNEL_DATA_SELECTOR
    mov ss, ax
    mov ds, ax
    mov es, ax
    xor eax, eax
    mov fs, ax
    mov gs, ax
    xor eax, eax
    ret

; Encodes one 64-bit available TSS descriptor at selector 0x28.
populate_tss_descriptor:
    lea rdx, [rel governed_tss]
    mov rax, TSS_LIMIT
    mov rcx, rdx
    and rcx, 0x00ffffff
    shl rcx, 16
    or rax, rcx
    mov rcx, TSS_AVAILABLE_ACCESS
    shl rcx, 40
    or rax, rcx
    mov rcx, rdx
    shr rcx, 24
    and rcx, 0xff
    shl rcx, 56
    or rax, rcx
    mov [rel governed_gdt + 40], rax
    mov rax, rdx
    shr rax, 32
    mov [rel governed_gdt + 48], eax
    mov dword [rel governed_gdt + 52], 0
    ret

; Loads the one boot-owned TSS and verifies TR immediately.
load_governed_tss:
    mov ax, TSS_SELECTOR
    ltr ax
    str ax
    mov [rel observed_task_register], ax
    cmp ax, TSS_SELECTOR
    jne .invalid
    xor eax, eax
    ret
.invalid:
    mov eax, PRIVILEGE_TSS_INVALID
    ret

; Populates vector 0x81 and fixed non-recovering fault sinks.
initialize_governed_idt:
    mov edi, KOZO_PRIVILEGE_RETURN_VECTOR
    lea rsi, [rel privilege_return_handler]
    mov edx, INTERRUPT_GATE_DPL3
    xor ecx, ecx
    call set_idt_gate

    mov edi, 6
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate
    mov edi, 8
    lea rsi, [rel privilege_double_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    mov ecx, DOUBLE_FAULT_IST_INDEX
    call set_idt_gate
    mov edi, 10
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate
    mov edi, 11
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate
    mov edi, 12
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate
    mov edi, 13
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate
    mov edi, 14
    lea rsi, [rel privilege_fault_sink]
    mov edx, INTERRUPT_GATE_DPL0
    xor ecx, ecx
    call set_idt_gate

    mov word [rel governed_idtr], IDT_LIMIT
    lea rax, [rel governed_idt]
    mov [rel governed_idtr + 2], rax
    lidt [rel governed_idtr]
    xor eax, eax
    ret

; Input: edi=vector, rsi=handler, edx=type/DPL, ecx=IST.
set_idt_gate:
    lea r8, [rel governed_idt]
    shl rdi, 4
    add r8, rdi
    mov word [r8], si
    mov word [r8 + 2], KERNEL_CODE_SELECTOR
    mov byte [r8 + 4], cl
    mov byte [r8 + 5], dl
    mov rax, rsi
    shr rax, 16
    mov word [r8 + 6], ax
    shr rax, 16
    mov dword [r8 + 8], eax
    mov dword [r8 + 12], 0
    ret

; Validates loaded tables, selectors, TSS state, and the fixed return gate.
validate_privilege_transition_tables:
    sgdt [rel observed_governed_gdtr]
    cmp word [rel observed_governed_gdtr], GDT_LIMIT
    jne .gdt_invalid
    lea rax, [rel governed_gdt]
    cmp [rel observed_governed_gdtr + 2], rax
    jne .gdt_invalid
    mov ax, cs
    cmp ax, KERNEL_CODE_SELECTOR
    jne .gdt_invalid
    mov ax, ss
    cmp ax, KERNEL_DATA_SELECTOR
    jne .gdt_invalid
    mov ax, ds
    cmp ax, KERNEL_DATA_SELECTOR
    jne .gdt_invalid
    mov ax, es
    cmp ax, KERNEL_DATA_SELECTOR
    jne .gdt_invalid
    mov rax, KERNEL_CODE_DESCRIPTOR
    cmp [rel governed_gdt + 8], rax
    jne .gdt_invalid
    mov rax, KERNEL_DATA_DESCRIPTOR
    cmp [rel governed_gdt + 16], rax
    jne .gdt_invalid
    mov rax, USER_DATA_DESCRIPTOR
    cmp [rel governed_gdt + 24], rax
    jne .gdt_invalid
    mov rax, USER_CODE_DESCRIPTOR
    cmp [rel governed_gdt + 32], rax
    jne .gdt_invalid

    str ax
    cmp ax, TSS_SELECTOR
    jne .tss_invalid
    lea rax, [rel privilege_return_stack_top]
    cmp [rel governed_tss + 4], rax
    jne .tss_invalid
    lea rax, [rel double_fault_stack_top]
    cmp [rel governed_tss + 36], rax
    jne .tss_invalid
    cmp word [rel governed_tss + 102], TSS_SIZE
    jne .tss_invalid
    mov al, [rel governed_gdt + 45]
    cmp al, TSS_BUSY_ACCESS
    jne .tss_invalid

    sidt [rel observed_governed_idtr]
    cmp word [rel observed_governed_idtr], IDT_LIMIT
    jne .idt_invalid
    lea rax, [rel governed_idt]
    cmp [rel observed_governed_idtr + 2], rax
    jne .idt_invalid
    call validate_privilege_return_gate
    test eax, eax
    jnz .idt_invalid
    xor eax, eax
    ret
.gdt_invalid:
    mov eax, PRIVILEGE_GDT_INVALID
    ret
.tss_invalid:
    mov eax, PRIVILEGE_TSS_INVALID
    ret
.idt_invalid:
    mov eax, PRIVILEGE_IDT_INVALID
    ret

; Validates vector 0x81 as one fixed DPL3 interrupt gate.
validate_privilege_return_gate:
    lea r8, [rel governed_idt + KOZO_PRIVILEGE_RETURN_VECTOR * 16]
    cmp word [r8 + 2], KERNEL_CODE_SELECTOR
    jne .invalid
    cmp byte [r8 + 4], 0
    jne .invalid
    cmp byte [r8 + 5], INTERRUPT_GATE_DPL3
    jne .invalid
    movzx rax, word [r8]
    movzx rdx, word [r8 + 6]
    shl rdx, 16
    or rax, rdx
    mov edx, [r8 + 8]
    shl rdx, 32
    or rax, rdx
    lea rdx, [rel privilege_return_handler]
    cmp rax, rdx
    jne .invalid
    xor eax, eax
    ret
.invalid:
    mov eax, 1
    ret

; Reuses the governed page walker for every entry and stack boundary.
validate_user_probe_entry:
    mov rdi, USER_PROBE_CODE_VA
    mov rsi, PTE_PRESENT | PTE_USER
    call require_mapping_flags
    test eax, eax
    jnz .entry_invalid
    mov rdi, USER_PROBE_DATA_VA
    mov rsi, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov rax, PTE_NX
    or rsi, rax
    call require_mapping_flags
    test eax, eax
    jnz .entry_invalid
    mov rdi, USER_PROBE_STACK_VA
    mov rsi, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov rax, PTE_NX
    or rsi, rax
    call require_mapping_flags
    test eax, eax
    jnz .stack_invalid

    lea rdi, [rel privilege_return_stack]
    call require_supervisor_rw_nx
    test eax, eax
    jnz .stack_invalid
    lea rdi, [rel double_fault_stack]
    call require_supervisor_rw_nx
    test eax, eax
    jnz .stack_invalid
    lea rdi, [rel governed_gdt]
    call require_supervisor_rw_nx
    test eax, eax
    jnz .entry_invalid
    lea rdi, [rel governed_tss]
    call require_supervisor_rw_nx
    test eax, eax
    jnz .entry_invalid
    lea rdi, [rel governed_idt]
    call require_supervisor_rw_nx
    test eax, eax
    jnz .entry_invalid

    lea rdi, [rel user_probe_code_start]
    call walk_page_mapping
    or rax, rdx
    jnz .entry_invalid
    mov rdi, USER_PROBE_DATA_VA
    cmp qword [rdi], 0
    jne .entry_invalid
    mov rax, USER_INITIAL_RSP
    test rax, 0xf
    jnz .stack_invalid
    mov rdx, USER_PROBE_STACK_VA
    cmp rax, rdx
    jbe .stack_invalid
    mov rdx, USER_PROBE_STACK_TOP_VA
    cmp rax, rdx
    jae .stack_invalid
    xor eax, eax
    ret
.entry_invalid:
    mov eax, PRIVILEGE_USER_ENTRY_INVALID
    ret
.stack_invalid:
    mov eax, PRIVILEGE_USER_STACK_INVALID
    ret

require_supervisor_rw_nx:
    mov rsi, PTE_PRESENT | PTE_WRITABLE
    mov rax, PTE_NX
    or rsi, rax
    jmp require_mapping_flags

; Input: rdi=virtual address, rsi=exact effective flags.
require_mapping_flags:
    push rsi
    call walk_page_mapping
    pop rcx
    test rax, rax
    jz .invalid
    cmp rdx, rcx
    jne .invalid
    xor eax, eax
    ret
.invalid:
    mov eax, 1
    ret

; Saves a fixed kernel continuation, emits entry-attempt evidence, and iretq's.
enter_bounded_ring3_probe:
    mov [rel saved_kernel_continuation_rsp], rsp
    mov qword [rel privilege_probe_state], 0
    mov rdi, USER_PROBE_DATA_VA
    cmp qword [rdi], 0
    jne .probe_failed
    call runtime_serial_write_ring3_enter_marker
    mov ax, USER_DATA_SELECTOR
    mov ds, ax
    mov es, ax
    push qword USER_DATA_SELECTOR
    mov rax, USER_INITIAL_RSP
    push rax
    push qword USER_RFLAGS
    push qword USER_CODE_SELECTOR
    mov rax, USER_PROBE_CODE_VA
    push rax
    iretq
    ud2
.probe_failed:
    mov eax, PRIVILEGE_USER_PROBE_FAILED
    ret

; Validates the hardware CPL3 frame on TSS.RSP0 and never returns to Ring 3.
privilege_return_handler:
    mov ax, KERNEL_DATA_SELECTOR
    mov ss, ax
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov r15, rsp
    call validate_ring3_return_frame
    test eax, eax
    jnz privilege_return_failure
    mov rdi, USER_PROBE_DATA_VA
    mov rax, USER_PROBE_TOKEN
    cmp [rdi], rax
    jne .probe_failed
    mov qword [rdi], 0
    cmp qword [rdi], 0
    jne .probe_failed
    mov rax, PRIVILEGE_PROBE_SUCCESS_STATE
    mov [rel privilege_probe_state], rax
    call runtime_serial_write_ring3_probe_marker
    mov rsp, [rel saved_kernel_continuation_rsp]
    jmp privilege_ring0_continuation
.probe_failed:
    mov eax, PRIVILEGE_USER_PROBE_FAILED
    jmp privilege_return_failure

; Validates CS/SS, user RIP/RSP/RFLAGS, CPL0, and TSS stack ownership.
validate_ring3_return_frame:
    mov ax, cs
    test ax, 3
    jnz .invalid
    lea rax, [rel privilege_return_stack]
    cmp r15, rax
    jb .invalid
    lea rax, [rel privilege_return_stack_top]
    sub rax, 40
    cmp r15, rax
    jne .invalid
    cmp qword [r15 + 8], USER_CODE_SELECTOR
    jne .invalid
    mov rax, [r15 + 8]
    and eax, 3
    cmp eax, 3
    jne .invalid
    cmp qword [r15 + 32], USER_DATA_SELECTOR
    jne .invalid
    mov rax, [r15 + 32]
    and eax, 3
    cmp eax, 3
    jne .invalid
    mov rax, USER_PROBE_CODE_VA + (user_privilege_probe_after_interrupt - user_probe_code_start)
    cmp [r15], rax
    jne .invalid
    mov rax, USER_INITIAL_RSP
    cmp [r15 + 24], rax
    jne .invalid
    cmp qword [r15 + 16], USER_RFLAGS
    jne .invalid
    xor eax, eax
    ret
.invalid:
    mov eax, PRIVILEGE_RETURN_FRAME_INVALID
    ret

privilege_return_failure:
    mov rsp, [rel saved_kernel_continuation_rsp]
    test rsp, rsp
    jz boot_terminal_halt
    ret

; Fixed continuation validates restored CPL0 state and returns to the boot caller.
privilege_ring0_continuation:
    mov ax, cs
    test ax, 3
    jnz .failed
    mov ax, ss
    cmp ax, KERNEL_DATA_SELECTOR
    jne .failed
    cmp rsp, [rel saved_kernel_continuation_rsp]
    jne .failed
    mov rax, PRIVILEGE_PROBE_SUCCESS_STATE
    cmp [rel privilege_probe_state], rax
    jne .failed
    mov rdi, USER_PROBE_DATA_VA
    cmp qword [rdi], 0
    jne .failed
    mov qword [rel privilege_probe_state], 0
    xor eax, eax
    ret
.failed:
    mov qword [rel privilege_probe_state], 0
    mov eax, PRIVILEGE_RING0_CONTINUATION_FAILED
    ret

privilege_fault_sink:
    cli
    jmp boot_terminal_halt

privilege_double_fault_sink:
    cli
    jmp boot_terminal_halt
