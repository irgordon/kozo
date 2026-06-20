bits 64

extern kernel_entry
global _start

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

section .bss
align 16
boot_stack:
    resb 16384
boot_stack_top:

section .note.GNU-stack
section .rodata

early_entry_marker:
    db "KOZO_EARLY_0_ENTRY", 13, 10
early_entry_marker_end:

section .text

_start:
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
    lea rsi, [rel early_entry_marker]
    mov rcx, early_entry_marker_end - early_entry_marker
    cld
.entry_marker_loop:
    mov dx, COM1_LINE_STATUS
    in al, dx
    test al, TRANSMIT_READY
    jz .entry_marker_loop
    lodsb
    mov dx, COM1
    out dx, al
    loop .entry_marker_loop
    xor rbp, rbp
    lea rsp, [rel boot_stack_top]
    and rsp, -16
    call kernel_entry

.hang:
    hlt
    jmp .hang
