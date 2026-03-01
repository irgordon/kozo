/* * KOZO Kernel Linker Script (x86_64)
 * * Last Modified: 2026-02-28, 22:15:42.112
 * * Target: UEFI Boot with ELF64 Loading
 * Physical Address (LMA): 4MB (0x400000)
 * Virtual Address (VMA):  -2GB (0xffffffff80000000)
 */

ENTRY(_kernel_start)

SECTIONS
{
    /* 1. Define the Constants */
    _kernel_vma_base = 0xffffffff80000000;
    _kernel_phys_base = 4M;

    /* 2. Set the Virtual Counter to the Higher-Half */
    . = _kernel_vma_base;

    /* 3. Text Section (Code) */
    /* AT() specifies the Load Memory Address (LMA) for the ELF Program Header */
    .text : AT(_kernel_phys_base) {
        _text_start = .;
        *(.text*)
        . = ALIGN(4K);
        _text_end = .;
    }

    /* 4. Read-Only Data */
    /* LMA calculation: current_virtual - vma_base + phys_base */
    .rodata : AT(ADDR(.rodata) - _kernel_vma_base + _kernel_phys_base) {
        _rodata_start = .;
        *(.rodata*)
        . = ALIGN(4K);
        _rodata_end = .;
    }

    /* 5. Initialized Data */
    .data : AT(ADDR(.data) - _kernel_vma_base + _kernel_phys_base) {
        _data_start = .;
        *(.data*)
        . = ALIGN(4K);
        _data_end = .;
    }

    /* 6. Uninitialized Data (BSS) and Stack */
    .bss : AT(ADDR(.bss) - _kernel_vma_base + _kernel_phys_base) {
        _bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(16);
        
        /* The Kernel Stack: Initialized here in the BSS */
        stack_bottom = .;
        . += 16384;      /* 16KB Stack */
        stack_top = .;
        
        _bss_end = .;
    }

    /* 7. End of Kernel marker (Physical) */
    _kernel_phys_end = . - _kernel_vma_base + _kernel_phys_base;

    /* Discard unnecessary sections */
    /DISCARD/ : {
        *(.comment)
        *(.eh_frame)
        *(.note.gnu.build-id)
    }
}