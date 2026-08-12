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
  ASSERT(user_privilege_probe_start == user_probe_code_start,
         "user privilege probe must begin at the user code page")
  ASSERT(user_privilege_probe_end <= user_probe_code_end,
         "user privilege probe must remain inside one code page")
  ASSERT((user_probe_data_end - user_probe_data_start) == 4K,
         "user probe data backing must be one page")
  ASSERT((user_probe_stack_top - user_probe_stack) == 4K,
         "user probe stack backing must be one page")
  ASSERT((governed_page_tables_end - governed_page_tables_start) == 28K,
         "governed page-table storage must be seven pages")
  ASSERT((governed_gdt_end - governed_gdt) == 56,
         "governed GDT must contain seven descriptor slots")
  ASSERT((governed_tss_end - governed_tss) == 104,
         "governed TSS must be exactly 104 bytes")
  ASSERT((governed_idt_end - governed_idt) == 4K,
         "governed IDT must be exactly one page")
  ASSERT((privilege_return_stack_top - privilege_return_stack) == 4K,
         "privilege return stack must be exactly one page")
  ASSERT((double_fault_stack_top - double_fault_stack) == 4K,
         "double-fault stack must be exactly one page")
  ASSERT((fixed_user_request_shadow_end - fixed_user_request_shadow) == 40,
         "fixed user request shadow must be exactly 40 bytes")
  ASSERT((fixed_user_response_shadow_end - fixed_user_response_shadow) == 88,
         "fixed user response shadow must be exactly 88 bytes")
  ASSERT((fixed_user_response_verify_end - fixed_user_response_verify) == 88,
         "fixed user response verify buffer must be exactly 88 bytes")
  ASSERT((fixed_user_consumption_shadow_end - fixed_user_consumption_shadow) == 48,
         "fixed user consumption shadow must be exactly 48 bytes")
  ASSERT((fixed_user_transaction_phase_end - fixed_user_transaction_phase) == 8,
         "fixed user transaction phase must be exactly 8 bytes")
  ASSERT((fixed_user_context_end - fixed_user_context) == 128,
         "fixed user execution context must be exactly 128 bytes")
  ASSERT((fixed_user_context % 16) == 0,
         "fixed user execution context must be 16-byte aligned")
  ASSERT((fixed_user_context_result_end - fixed_user_context_result) == 32,
         "fixed user execution context result must be exactly 32 bytes")
  ASSERT((fixed_user_context_result % 8) == 0,
         "fixed user execution context result must be 8-byte aligned")
  ASSERT(fixed_user_transaction_phase_end <= fixed_user_context,
         "fixed user execution context must not overlap transaction phase")
  ASSERT(fixed_user_context_end <= fixed_user_context_result,
         "fixed user execution context and result must not overlap")
  ASSERT(fixed_user_context_result_end <= fixed_user_request_success_state,
         "fixed user execution context result must not overlap runtime state")
  ASSERT((fixed_user_request_shadow % 8) == 0,
         "fixed user request shadow must be 8-byte aligned")
  ASSERT((fixed_user_response_shadow % 8) == 0,
         "fixed user response shadow must be 8-byte aligned")
  ASSERT((fixed_user_response_verify % 8) == 0,
         "fixed user response verify buffer must be 8-byte aligned")
  ASSERT((fixed_user_consumption_shadow % 8) == 0,
         "fixed user consumption shadow must be 8-byte aligned")
  ASSERT((fixed_user_transaction_phase % 8) == 0,
         "fixed user transaction phase must be 8-byte aligned")
  ASSERT(DEFINED(runtime_status_snapshot),
         "runtime status snapshot must be linked")
  ASSERT((runtime_status_snapshot % 8) == 0,
         "runtime status snapshot must be 8-byte aligned")
  ASSERT(user_response_consumer_start >= user_probe_code_start,
         "user response consumer must start inside the user code page")
  ASSERT(user_response_consumer_end <= user_probe_code_end,
         "user response consumer must remain inside the user code page")
  ASSERT((__kernel_loaded_image_end - __kernel_image_start) < 2M,
         "fixed kernel mappings must fit one page table")
}
