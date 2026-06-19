bits 64

global memset
global memmove

section .note.GNU-stack
section .text

memset:
    mov rax, rdi
    mov rcx, rdx
    movzx rsi, sil
    test rcx, rcx
    jz .done
.loop:
    mov byte [rdi], sil
    inc rdi
    dec rcx
    jnz .loop
.done:
    ret

memmove:
    mov rax, rdi
    cmp rdi, rsi
    je .done
    test rdx, rdx
    jz .done
    jb .forward
    lea r8, [rsi + rdx]
    cmp rdi, r8
    jae .forward
    lea rdi, [rdi + rdx - 1]
    lea rsi, [rsi + rdx - 1]
.backward:
    mov r8b, [rsi]
    mov [rdi], r8b
    dec rsi
    dec rdi
    dec rdx
    jnz .backward
    ret
.forward:
    mov rcx, rdx
.forward_loop:
    mov r8b, [rsi]
    mov [rdi], r8b
    inc rsi
    inc rdi
    dec rcx
    jnz .forward_loop
.done:
    ret
