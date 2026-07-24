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
RUNTIME_LOOP_INVALID_LIMIT :: u32(3)
RUNTIME_LOOP_INVALID_INITIAL_STATE :: u32(4)
RUNTIME_LOOP_ITERATION_STATE_MISMATCH :: u32(5)
RUNTIME_LOOP_ACCUMULATOR_MISMATCH :: u32(6)
RUNTIME_LOOP_TERMINAL_COUNT_MISMATCH :: u32(7)
RUNTIME_LOOP_TERMINAL_STATUS_MISMATCH :: u32(8)

RUNTIME_LOOP_ITERATION_LIMIT :: u64(3)
RUNTIME_LOOP_EXPECTED_ACCUMULATOR :: u64(6)
RUNTIME_LOOP_STATUS_IDLE :: u32(0)
RUNTIME_LOOP_STATUS_RUNNING :: u32(1)
RUNTIME_LOOP_STATUS_COMPLETED :: u32(2)

@require foreign import runtime_boot_bridge "arch/x86_64/boot.asm"

foreign runtime_boot_bridge {
	runtime_serial_write_init_marker :: proc "c" () ---
	runtime_serial_write_loop_enter_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_1_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_2_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_3_marker :: proc "c" () ---
	runtime_serial_write_loop_exit_marker :: proc "c" () ---
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

Runtime_Loop_State :: struct {
	iteration_limit: u64,
	iteration_count: u64,
	accumulator:     u64,
	status:          u32,
	reserved:        u32,
}

@(export)
runtime_progression_state: u64

@(export)
runtime_loop_state: Runtime_Loop_State

@(export)
runtime_progression_entry :: proc "c" (bootstrap: ^Runtime_Bootstrap_Context) -> u32 {
	if !runtime_bootstrap_context_is_valid(bootstrap) {
		return RUNTIME_PROGRESSION_INVALID_CONTEXT
	}
	if !runtime_state_probe_succeeds() {
		return RUNTIME_PROGRESSION_STATE_FAILURE
	}
	runtime_emit_init_marker()
	return controlled_runtime_loop()
}

@(export)
controlled_runtime_loop :: proc "contextless" () -> u32 {
	runtime_loop_reset_state()
	if runtime_loop_limit() != RUNTIME_LOOP_ITERATION_LIMIT {
		return RUNTIME_LOOP_INVALID_LIMIT
	}
	if !runtime_loop_initial_state_is_valid() {
		return RUNTIME_LOOP_INVALID_INITIAL_STATE
	}
	runtime_serial_write_loop_enter_marker()
	runtime_loop_set_status(RUNTIME_LOOP_STATUS_RUNNING)

	for runtime_loop_iteration_count() < runtime_loop_limit() {
		status := runtime_loop_execute_iteration()
		if status != RUNTIME_PROGRESSION_OK {
			return status
		}
	}
	return runtime_loop_complete()
}

runtime_emit_init_marker :: proc "contextless" () {
	runtime_serial_write_init_marker()
}

runtime_loop_reset_state :: proc "contextless" () {
	intrinsics.volatile_store(&runtime_loop_state.iteration_limit, RUNTIME_LOOP_ITERATION_LIMIT)
	intrinsics.volatile_store(&runtime_loop_state.iteration_count, 0)
	intrinsics.volatile_store(&runtime_loop_state.accumulator, 0)
	intrinsics.volatile_store(&runtime_loop_state.status, RUNTIME_LOOP_STATUS_IDLE)
	intrinsics.volatile_store(&runtime_loop_state.reserved, 0)
}

runtime_loop_initial_state_is_valid :: proc "contextless" () -> bool {
	return runtime_loop_iteration_count() == 0 &&
	       runtime_loop_accumulator() == 0 &&
	       runtime_loop_status() == RUNTIME_LOOP_STATUS_IDLE &&
	       runtime_loop_reserved() == 0
}

runtime_loop_execute_iteration :: proc "contextless" () -> u32 {
	next_count := runtime_loop_iteration_count() + 1
	next_accumulator := runtime_loop_accumulator() + next_count
	intrinsics.volatile_store(&runtime_loop_state.iteration_count, next_count)
	intrinsics.volatile_store(&runtime_loop_state.accumulator, next_accumulator)
	if !runtime_loop_iteration_state_is_valid(next_count) {
		return RUNTIME_LOOP_ITERATION_STATE_MISMATCH
	}
	if next_accumulator != runtime_loop_expected_accumulator(next_count) {
		return RUNTIME_LOOP_ACCUMULATOR_MISMATCH
	}
	if !runtime_emit_loop_iteration_marker(next_count) {
		return RUNTIME_LOOP_ITERATION_STATE_MISMATCH
	}
	return RUNTIME_PROGRESSION_OK
}

runtime_loop_iteration_state_is_valid :: proc "contextless" (expected_count: u64) -> bool {
	return runtime_loop_iteration_count() == expected_count &&
	       runtime_loop_status() == RUNTIME_LOOP_STATUS_RUNNING &&
	       runtime_loop_reserved() == 0 &&
	       expected_count <= runtime_loop_limit()
}

runtime_loop_expected_accumulator :: proc "contextless" (count: u64) -> u64 {
	switch count {
	case 1:
		return 1
	case 2:
		return 3
	case 3:
		return 6
	}
	return 0
}

runtime_emit_loop_iteration_marker :: proc "contextless" (count: u64) -> bool {
	switch count {
	case 1:
		runtime_serial_write_loop_iter_1_marker()
	case 2:
		runtime_serial_write_loop_iter_2_marker()
	case 3:
		runtime_serial_write_loop_iter_3_marker()
	case:
		return false
	}
	return true
}

runtime_loop_complete :: proc "contextless" () -> u32 {
	if runtime_loop_iteration_count() != runtime_loop_limit() {
		return RUNTIME_LOOP_TERMINAL_COUNT_MISMATCH
	}
	if runtime_loop_accumulator() != RUNTIME_LOOP_EXPECTED_ACCUMULATOR {
		return RUNTIME_LOOP_ACCUMULATOR_MISMATCH
	}
	runtime_loop_set_status(RUNTIME_LOOP_STATUS_COMPLETED)
	if runtime_loop_status() != RUNTIME_LOOP_STATUS_COMPLETED || runtime_loop_reserved() != 0 {
		return RUNTIME_LOOP_TERMINAL_STATUS_MISMATCH
	}
	runtime_serial_write_loop_exit_marker()
	return RUNTIME_PROGRESSION_OK
}

runtime_loop_limit :: proc "contextless" () -> u64 {
	return intrinsics.volatile_load(&runtime_loop_state.iteration_limit)
}

runtime_loop_iteration_count :: proc "contextless" () -> u64 {
	return intrinsics.volatile_load(&runtime_loop_state.iteration_count)
}

runtime_loop_accumulator :: proc "contextless" () -> u64 {
	return intrinsics.volatile_load(&runtime_loop_state.accumulator)
}

runtime_loop_status :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&runtime_loop_state.status)
}

runtime_loop_reserved :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&runtime_loop_state.reserved)
}

runtime_loop_set_status :: proc "contextless" (status: u32) {
	intrinsics.volatile_store(&runtime_loop_state.status, status)
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
