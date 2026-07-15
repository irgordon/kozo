package kernel

import "base:intrinsics"

RUNTIME_BOOTSTRAP_VERSION :: u64(1)
RUNTIME_BOOTSTRAP_SIZE :: u64(64)
RUNTIME_BOOT_STACK_SIZE :: u64(16384)
RUNTIME_BOOT_MEMORY_SIZE :: u64(4096)
RUNTIME_STATE_SENTINEL :: u64(0x4b4f5a4f52554e31)

RUNTIME_PROGRESSION_OK :: u32(0)
RUNTIME_PROGRESSION_INVALID_CONTEXT :: u32(1)
RUNTIME_PROGRESSION_STATE_FAILURE :: u32(2)

@require foreign import runtime_boot_bridge "arch/x86_64/boot.asm"

foreign runtime_boot_bridge {
	runtime_serial_write_init_marker :: proc "c" () ---
}

Runtime_Bootstrap_Context :: struct {
	version:             u64,
	structure_size:      u64,
	stack_base:          u64,
	stack_top:           u64,
	memory_region_start: u64,
	memory_region_end:   u64,
	flags:               u64,
	reserved:            u64,
}

@(export)
runtime_progression_state: u64

@(export)
runtime_progression_entry :: proc "c" (bootstrap: ^Runtime_Bootstrap_Context) -> u32 {
	if !runtime_bootstrap_context_is_valid(bootstrap) {
		return RUNTIME_PROGRESSION_INVALID_CONTEXT
	}
	if !runtime_state_probe_succeeds() {
		return RUNTIME_PROGRESSION_STATE_FAILURE
	}
	runtime_emit_init_marker()
	return RUNTIME_PROGRESSION_OK
}

runtime_emit_init_marker :: proc "contextless" () {
	runtime_serial_write_init_marker()
}

runtime_bootstrap_context_is_valid :: proc "contextless" (bootstrap: ^Runtime_Bootstrap_Context) -> bool {
	if bootstrap == nil {
		return false
	}
	return runtime_bootstrap_header_is_valid(bootstrap) &&
	       runtime_stack_range_is_valid(bootstrap) &&
	       runtime_memory_range_is_valid(bootstrap)
}

runtime_bootstrap_header_is_valid :: proc "contextless" (bootstrap: ^Runtime_Bootstrap_Context) -> bool {
	return bootstrap.version == RUNTIME_BOOTSTRAP_VERSION &&
	       bootstrap.structure_size == RUNTIME_BOOTSTRAP_SIZE &&
	       bootstrap.flags == 0 &&
	       bootstrap.reserved == 0
}

runtime_stack_range_is_valid :: proc "contextless" (bootstrap: ^Runtime_Bootstrap_Context) -> bool {
	return ordered_range_has_size(bootstrap.stack_base, bootstrap.stack_top, RUNTIME_BOOT_STACK_SIZE) &&
	       bootstrap.stack_base % 16 == 0 &&
	       bootstrap.stack_top % 16 == 0
}

runtime_memory_range_is_valid :: proc "contextless" (bootstrap: ^Runtime_Bootstrap_Context) -> bool {
	return ordered_range_has_size(
		bootstrap.memory_region_start,
		bootstrap.memory_region_end,
		RUNTIME_BOOT_MEMORY_SIZE,
	) && bootstrap.memory_region_start % RUNTIME_BOOT_MEMORY_SIZE == 0
}

ordered_range_has_size :: proc "contextless" (start, end, expected_size: u64) -> bool {
	return end > start && end - start == expected_size
}

runtime_state_probe_succeeds :: proc "contextless" () -> bool {
	intrinsics.volatile_store(&runtime_progression_state, RUNTIME_STATE_SENTINEL)
	observed := intrinsics.volatile_load(&runtime_progression_state)
	intrinsics.volatile_store(&runtime_progression_state, 0)
	restored := intrinsics.volatile_load(&runtime_progression_state)
	return observed == RUNTIME_STATE_SENTINEL && restored == 0
}
