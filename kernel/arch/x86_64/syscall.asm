bits 64

extern syscall_dispatch
global syscall_entry

section .note.GNU-stack
section .text

syscall_entry:
    push r11
    push rcx
    sub rsp, 8

    mov rdi, rax
    mov rsi, rbx
    call syscall_dispatch

    add rsp, 8
    pop rcx
    pop r11
    ret
