bits 64

extern syscall_dispatch
global syscall_entry
global x86_read_timestamp
global x86_halt
global x86_outb
global x86_inb

section .note.GNU-stack
section .text

syscall_entry:
    push rbx
    push r11
    push rcx
    sub rsp, 8

    mov rax, rdi
    mov rbx, rsi
    mov rdi, rax
    mov rsi, rbx
    call syscall_dispatch

    add rsp, 8
    pop rcx
    pop r11
    pop rbx
    ret

x86_read_timestamp:
    rdtsc
    shl rdx, 32
    or rax, rdx
    ret

x86_halt:
    hlt
    ret

x86_outb:
    mov edx, edi
    mov al, sil
    out dx, al
    ret

x86_inb:
    mov edx, edi
    in al, dx
    ret
