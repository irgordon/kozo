/* kernel/arch/x86_64/linker.ld */
/* Last Modified: 2026-02-28, 21:03:12.118 */

ENTRY(_start)

PHDRS {
    boot PT_LOAD FLAGS(7);
    note PT_NOTE FLAGS(4);
    text PT_LOAD FLAGS(5);
    data PT_LOAD FLAGS(6);
}

SECTIONS {
    . = 2M;
    _phys_boot_start = .;
    .note : AT(_phys_boot_start) { KEEP(*(.note.Xen)) } :note
    .boot : AT(_phys_boot_start + SIZEOF(.note)) {
        *(.boot.text)
        *(.boot.data)
        . = ALIGN(4096);
    } :boot
    
    . = ALIGN(4M);
    _kernel_phys_start = .;
    _kernel_vma_base = 0xffffffff80000000;
    . = _kernel_vma_base;

    .text : AT(_kernel_phys_start) {
        _text_start = .;
        *(.text*)
        . = ALIGN(4096);
    } :text
    
    .rodata : AT(. - _kernel_vma_base + _kernel_phys_start) { *(.rodata*) . = ALIGN(4096); } :data
    .data : AT(. - _kernel_vma_base + _kernel_phys_start) { *(.data*) . = ALIGN(4096); } :data
    .bss : AT(. - _kernel_vma_base + _kernel_phys_start) {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(16);
        stack_bottom = .;
        . += 16384;
        stack_top = .;
        _bss_end = .;
    } :data
}