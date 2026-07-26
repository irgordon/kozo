OUTPUT_FORMAT(elf64-x86-64)
ENTRY(_start)

KERNEL_VMA = 0xffffffff80200000;
KERNEL_LMA = 0x200000;

SECTIONS
{
  . = KERNEL_VMA;
  __kernel_image_start = .;

  . = ALIGN(4K);
  __kernel_text_start = .;
  .text : AT(ADDR(.text) - KERNEL_VMA + KERNEL_LMA) {
    *(.text .text.*)
  }
  __kernel_text_end = .;

  . = ALIGN(4K);
  __user_probe_code_backing_start = .;
  .user_probe_code : AT(ADDR(.user_probe_code) - KERNEL_VMA + KERNEL_LMA) {
    *(.user_probe_code)
  }
  __user_probe_code_backing_end = .;

  . = ALIGN(4K);
  __kernel_rodata_start = .;
  .rodata : AT(ADDR(.rodata) - KERNEL_VMA + KERNEL_LMA) {
    *(.rodata .rodata.*)
    *(.odinti .odinti.*)
    *(.eh_frame .eh_frame.*)
  }
  __kernel_rodata_end = .;

  . = ALIGN(4K);
  __kernel_data_start = .;
  .data : AT(ADDR(.data) - KERNEL_VMA + KERNEL_LMA) {
    KEEP(*(.limine_requests_start))
    KEEP(*(.limine_requests))
    KEEP(*(.limine_requests_end))
    *(.data .data.*)
    *(.got .got.*)
  }
  __kernel_data_end = .;

  . = ALIGN(4K);
  __kernel_bss_start = .;
  .bss : AT(ADDR(.bss) - KERNEL_VMA + KERNEL_LMA) {
    *(COMMON)
    *(.bss .bss.*)
  }
  .tbss : AT(ADDR(.tbss) - KERNEL_VMA + KERNEL_LMA) {
    *(.tbss .tbss.*)
  }
  __kernel_bss_end = .;

  . = ALIGN(4K);
  .user_probe_data : AT(ADDR(.user_probe_data) - KERNEL_VMA + KERNEL_LMA) {
    *(.user_probe_data)
  }

  . = ALIGN(4K);
  .user_probe_stack : AT(ADDR(.user_probe_stack) - KERNEL_VMA + KERNEL_LMA) {
    *(.user_probe_stack)
  }

  . = ALIGN(4K);
  .paging_tables : AT(ADDR(.paging_tables) - KERNEL_VMA + KERNEL_LMA) {
    *(.paging_tables)
  }
  __kernel_loaded_image_end = .;

  ASSERT((user_probe_code_end - user_probe_code_start) == 4K,
         "user probe code backing must be one page")
  ASSERT((user_probe_data_end - user_probe_data_start) == 4K,
         "user probe data backing must be one page")
  ASSERT((user_probe_stack_top - user_probe_stack) == 4K,
         "user probe stack backing must be one page")
  ASSERT((governed_page_tables_end - governed_page_tables_start) == 28K,
         "governed page-table storage must be seven pages")
  ASSERT((__kernel_loaded_image_end - __kernel_image_start) < 2M,
         "fixed kernel mappings must fit one page table")
}
