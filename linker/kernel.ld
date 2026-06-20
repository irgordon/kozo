OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)

KERNEL_VMA = 0xffffffff80200000;
KERNEL_LMA = 0x200000;

SECTIONS
{
  . = KERNEL_VMA;

  . = ALIGN(4K);
  .text : AT(ADDR(.text) - KERNEL_VMA + KERNEL_LMA) {
    *(.text .text.*)
  }

  . = ALIGN(4K);
  .rodata : AT(ADDR(.rodata) - KERNEL_VMA + KERNEL_LMA) {
    *(.rodata .rodata.*)
  }

  . = ALIGN(4K);
  .data : AT(ADDR(.data) - KERNEL_VMA + KERNEL_LMA) {
    *(.data .data.*)
  }

  . = ALIGN(4K);
  .bss : AT(ADDR(.bss) - KERNEL_VMA + KERNEL_LMA) {
    *(COMMON)
    *(.bss .bss.*)
  }
}
