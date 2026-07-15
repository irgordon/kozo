bits 64

extern kernel_entry
global _start
global boot_memory_region
global boot_memory_region_end

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
    cli

.halt:
    hlt
    jmp .halt
