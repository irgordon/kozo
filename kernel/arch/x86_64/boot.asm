bits 64

extern kernel_entry
global _start

section .bss
align 16
boot_stack:
    resb 16384
boot_stack_top:

section .note.GNU-stack
section .text

_start:
    xor rbp, rbp
    lea rsp, [rel boot_stack_top]
    and rsp, -16
    call kernel_entry

.hang:
    hlt
    jmp .hang
