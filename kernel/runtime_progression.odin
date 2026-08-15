package kernel

import "base:intrinsics"

// This file owns the bounded Odin runtime sequence. It coordinates the
// completed loop, fixed user transaction, and internal capabilities without
// owning paging, privilege-transition mechanics, or terminal halt behavior.

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

REPEATED_SESSION_COORDINATOR_FORMAT_VERSION :: u32(1)
REPEATED_SESSION_COORDINATOR_SIZE :: u32(32)
REQUIRED_SESSION_COUNT :: u32(2)
FIRST_SESSION_ORDINAL :: u32(1)
SECOND_SESSION_ORDINAL :: u32(2)
PER_SESSION_TRANSITION_COUNT :: u32(2)
REQUIRED_TOTAL_TRANSITION_COUNT :: u32(4)
RUNTIME_REPEATED_SESSION_FAILURE :: u32(20)

REPEATED_SESSION_FAILURE_NONE :: u32(0)
REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_FORMAT :: u32(1)
REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_SIZE :: u32(2)
REPEATED_SESSION_FAILURE_INVALID_SESSION_ORDINAL :: u32(3)
REPEATED_SESSION_FAILURE_INVALID_REQUIRED_SESSION_COUNT :: u32(4)
REPEATED_SESSION_FAILURE_STALE_CONTEXT_BEFORE_SESSION :: u32(5)
REPEATED_SESSION_FAILURE_STALE_CONTEXT_RESULT_BEFORE_SESSION :: u32(6)
REPEATED_SESSION_FAILURE_IDENTITY_REUSE :: u32(7)
REPEATED_SESSION_FAILURE_FIRST_SESSION :: u32(8)
REPEATED_SESSION_FAILURE_FIRST_SESSION_CLEANUP :: u32(9)
REPEATED_SESSION_FAILURE_FIRST_RESULT_RESET :: u32(10)
REPEATED_SESSION_FAILURE_SECOND_SESSION :: u32(11)
REPEATED_SESSION_FAILURE_SECOND_SESSION_CLEANUP :: u32(12)
REPEATED_SESSION_FAILURE_SECOND_RESULT_RESET :: u32(13)
REPEATED_SESSION_FAILURE_COMPLETED_COUNT :: u32(14)
REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT :: u32(15)
REPEATED_SESSION_FAILURE_UNEXPECTED_THIRD_SESSION :: u32(16)
REPEATED_SESSION_FAILURE_FINAL_VALIDATION :: u32(17)

@require foreign import runtime_boot_bridge "arch/x86_64/boot.asm"
@require foreign import runtime_privilege_bridge "arch/x86_64/privilege_transition.asm"

foreign runtime_boot_bridge {
	runtime_serial_write_init_marker :: proc "c" () ---
	runtime_serial_write_loop_enter_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_1_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_2_marker :: proc "c" () ---
	runtime_serial_write_loop_iter_3_marker :: proc "c" () ---
	runtime_serial_write_loop_exit_marker :: proc "c" () ---
	runtime_serial_write_capability_dispatch_marker :: proc "c" () ---
	runtime_serial_write_status_query_marker :: proc "c" () ---
	runtime_serial_write_first_capability_marker :: proc "c" () ---
	runtime_serial_write_state_update_enter_marker :: proc "c" () ---
	runtime_serial_write_state_update_ok_marker :: proc "c" () ---
	runtime_serial_write_second_capability_marker :: proc "c" () ---
}

foreign runtime_privilege_bridge {
	execute_fixed_user_runtime_status_transaction :: proc "c" () -> u32 ---
	validate_fixed_user_context_success_result :: proc "c" () -> u32 ---
	validate_fixed_user_session_cleanup :: proc "c" () -> u32 ---
	reset_fixed_user_context_result :: proc "c" () -> u32 ---
	reset_fixed_user_execution_context_for_reuse :: proc "c" () -> u32 ---
	validate_fixed_user_session_reset_state :: proc "c" () -> u32 ---
	validate_fixed_user_session_identity_sequence :: proc "c" () -> u32 ---
	invalidate_fixed_user_session_state :: proc "c" () -> u32 ---
	fixed_user_context_is_uninitialized :: proc "c" () -> u32 ---
	fixed_user_context_result_is_initial :: proc "c" () -> u32 ---
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

Repeated_User_Session_Coordinator :: struct #align(8) {
	format_version:                  u32,
	structure_size:                 u32,
	required_session_count:         u32,
	active_session_ordinal:         u32,
	completed_session_count:        u32,
	observed_total_transition_count: u32,
	failure_code:                   u32,
	reserved:                       u32,
}

#assert(size_of(Repeated_User_Session_Coordinator) == REPEATED_SESSION_COORDINATOR_SIZE)
#assert(align_of(Repeated_User_Session_Coordinator) == 8)

@(export)
runtime_progression_state: u64

@(export)
runtime_loop_state: Runtime_Loop_State

@(export)
repeated_user_session_coordinator: Repeated_User_Session_Coordinator

@(export)
runtime_progression_entry :: proc "c" (bootstrap: ^Runtime_Bootstrap_Context) -> u32 {
	if !runtime_bootstrap_context_is_valid(bootstrap) {
		return RUNTIME_PROGRESSION_INVALID_CONTEXT
	}
	if !runtime_state_probe_succeeds() {
		return RUNTIME_PROGRESSION_STATE_FAILURE
	}
	if !initialize_runtime_state_transition_cell() {
		return RUNTIME_PROGRESSION_STATE_FAILURE
	}
	runtime_emit_init_marker()
	loop_status := controlled_runtime_loop()
	if loop_status != RUNTIME_PROGRESSION_OK {
		return loop_status
	}
	status_boundary_result := execute_runtime_status_boundaries()
	if status_boundary_result != RUNTIME_PROGRESSION_OK {
		return status_boundary_result
	}
	return execute_second_governed_capability()
}

@(export)
execute_runtime_status_boundaries :: proc "contextless" () -> u32 {
	collection_status := collect_runtime_status()
	if collection_status != RUNTIME_PROGRESSION_OK {
		return collection_status
	}
	transaction_status := execute_bounded_repeated_user_sessions()
	if transaction_status != RUNTIME_PROGRESSION_OK {
		clear_runtime_status_snapshot()
		return transaction_status
	}
	capability_status := execute_first_governed_capability()
	if !clear_runtime_status_snapshot() {
		return RUNTIME_CAPABILITY_EXECUTION_FAILURE
	}
	return capability_status
}

@(export)
execute_bounded_repeated_user_sessions :: proc "contextless" () -> u32 {
	initialize_repeated_session_coordinator()
	initial_failure_code := repeated_session_initial_failure_code()
	if initial_failure_code != REPEATED_SESSION_FAILURE_NONE {
		return fail_repeated_user_sessions(initial_failure_code)
	}
	if execute_first_bounded_user_session() != RUNTIME_PROGRESSION_OK {
		return RUNTIME_REPEATED_SESSION_FAILURE
	}
	return execute_second_bounded_user_session()
}

@(export)
execute_first_bounded_user_session :: proc "contextless" () -> u32 {
	if execute_fixed_user_session(FIRST_SESSION_ORDINAL) != RUNTIME_PROGRESSION_OK {
		return RUNTIME_REPEATED_SESSION_FAILURE
	}
	return prepare_next_fixed_user_session()
}

@(export)
execute_second_bounded_user_session :: proc "contextless" () -> u32 {
	if execute_fixed_user_session(SECOND_SESSION_ORDINAL) != RUNTIME_PROGRESSION_OK {
		return RUNTIME_REPEATED_SESSION_FAILURE
	}
	return finalize_repeated_session_coordinator()
}

@(export)
execute_fixed_user_session :: proc "contextless" (session_ordinal: u32) -> u32 {
	begin_failure_code := begin_fixed_user_session(session_ordinal)
	if begin_failure_code != REPEATED_SESSION_FAILURE_NONE {
		return fail_repeated_user_sessions(begin_failure_code)
	}
	if !fixed_user_session_succeeds() {
		return fail_repeated_user_sessions(session_failure_code(session_ordinal))
	}
	return complete_fixed_user_session(session_ordinal)
}

@(export)
begin_fixed_user_session :: proc "contextless" (session_ordinal: u32) -> u32 {
	failure_code := next_fixed_user_session_failure_code(session_ordinal)
	if failure_code != REPEATED_SESSION_FAILURE_NONE {
		return failure_code
	}
	set_active_repeated_session_ordinal(session_ordinal)
	return REPEATED_SESSION_FAILURE_NONE
}

@(export)
fixed_user_session_succeeds :: proc "contextless" () -> bool {
	if execute_fixed_user_runtime_status_transaction() != RUNTIME_PROGRESSION_OK {
		return false
	}
	return validate_fixed_user_context_success_result() == RUNTIME_PROGRESSION_OK
}

@(export)
complete_fixed_user_session :: proc "contextless" (session_ordinal: u32) -> u32 {
	record_completed_fixed_user_session()
	failure_code := completed_session_failure_code(session_ordinal)
	if failure_code != REPEATED_SESSION_FAILURE_NONE {
		return fail_repeated_user_sessions(failure_code)
	}
	return RUNTIME_PROGRESSION_OK
}

@(export)
prepare_next_fixed_user_session :: proc "contextless" () -> u32 {
	return reset_completed_fixed_user_session(
		REPEATED_SESSION_FAILURE_FIRST_SESSION_CLEANUP,
		REPEATED_SESSION_FAILURE_FIRST_RESULT_RESET,
	)
}

@(export)
finalize_repeated_session_coordinator :: proc "contextless" () -> u32 {
	if reset_completed_fixed_user_session(
		REPEATED_SESSION_FAILURE_SECOND_SESSION_CLEANUP,
		REPEATED_SESSION_FAILURE_SECOND_RESULT_RESET,
	) != RUNTIME_PROGRESSION_OK {
		return RUNTIME_REPEATED_SESSION_FAILURE
	}
	terminal_failure_code := repeated_session_terminal_failure_code()
	if terminal_failure_code != REPEATED_SESSION_FAILURE_NONE {
		return fail_repeated_user_sessions(terminal_failure_code)
	}
	return RUNTIME_PROGRESSION_OK
}

@(export)
reset_completed_fixed_user_session :: proc "contextless" (
	cleanup_failure_code: u32,
	result_failure_code: u32,
) -> u32 {
	if validate_fixed_user_session_cleanup() != RUNTIME_PROGRESSION_OK {
		return fail_repeated_user_sessions(cleanup_failure_code)
	}
	if reset_fixed_user_context_result() != RUNTIME_PROGRESSION_OK {
		return fail_repeated_user_sessions(result_failure_code)
	}
	return reset_fixed_user_context_for_reuse(cleanup_failure_code)
}

@(export)
reset_fixed_user_context_for_reuse :: proc "contextless" (failure_code: u32) -> u32 {
	if reset_fixed_user_execution_context_for_reuse() != RUNTIME_PROGRESSION_OK {
		return fail_repeated_user_sessions(failure_code)
	}
	if validate_fixed_user_session_reset_state() != RUNTIME_PROGRESSION_OK {
		return fail_repeated_user_sessions(failure_code)
	}
	return RUNTIME_PROGRESSION_OK
}

@(export)
initialize_repeated_session_coordinator :: proc "contextless" () {
	intrinsics.volatile_store(&repeated_user_session_coordinator.format_version, REPEATED_SESSION_COORDINATOR_FORMAT_VERSION)
	intrinsics.volatile_store(&repeated_user_session_coordinator.structure_size, REPEATED_SESSION_COORDINATOR_SIZE)
	intrinsics.volatile_store(&repeated_user_session_coordinator.required_session_count, REQUIRED_SESSION_COUNT)
	intrinsics.volatile_store(&repeated_user_session_coordinator.active_session_ordinal, 0)
	intrinsics.volatile_store(&repeated_user_session_coordinator.completed_session_count, 0)
	intrinsics.volatile_store(&repeated_user_session_coordinator.observed_total_transition_count, 0)
	intrinsics.volatile_store(&repeated_user_session_coordinator.failure_code, REPEATED_SESSION_FAILURE_NONE)
	intrinsics.volatile_store(&repeated_user_session_coordinator.reserved, 0)
}

repeated_session_initial_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_format_version() != REPEATED_SESSION_COORDINATOR_FORMAT_VERSION {
		return REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_FORMAT
	}
	if repeated_session_structure_size() != REPEATED_SESSION_COORDINATOR_SIZE {
		return REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_SIZE
	}
	return repeated_session_required_count_failure_code()
}

repeated_session_required_count_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_required_count() != REQUIRED_SESSION_COUNT {
		return REPEATED_SESSION_FAILURE_INVALID_REQUIRED_SESSION_COUNT
	}
	return repeated_session_initial_authority_failure_code()
}

repeated_session_initial_authority_failure_code :: proc "contextless" () -> u32 {
	failure_code := reusable_fixed_user_authority_failure_code()
	if failure_code != REPEATED_SESSION_FAILURE_NONE {
		return failure_code
	}
	return repeated_session_initial_value_failure_code()
}

reusable_fixed_user_authority_failure_code :: proc "contextless" () -> u32 {
	if fixed_user_context_is_uninitialized() != RUNTIME_PROGRESSION_OK {
		return REPEATED_SESSION_FAILURE_STALE_CONTEXT_BEFORE_SESSION
	}
	if fixed_user_context_result_is_initial() != RUNTIME_PROGRESSION_OK {
		return REPEATED_SESSION_FAILURE_STALE_CONTEXT_RESULT_BEFORE_SESSION
	}
	return repeated_session_identity_failure_code()
}

repeated_session_identity_failure_code :: proc "contextless" () -> u32 {
	if validate_fixed_user_session_identity_sequence() != RUNTIME_PROGRESSION_OK {
		return REPEATED_SESSION_FAILURE_IDENTITY_REUSE
	}
	return REPEATED_SESSION_FAILURE_NONE
}

repeated_session_initial_value_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_active_ordinal() != 0 || repeated_session_completed_count() != 0 {
		return REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_FORMAT
	}
	if repeated_session_total_transition_count() != 0 {
		return REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT
	}
	return repeated_session_initial_metadata_failure_code()
}

repeated_session_initial_metadata_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_failure() != REPEATED_SESSION_FAILURE_NONE || repeated_session_reserved() != 0 {
		return REPEATED_SESSION_FAILURE_INVALID_COORDINATOR_FORMAT
	}
	return REPEATED_SESSION_FAILURE_NONE
}

next_fixed_user_session_failure_code :: proc "contextless" (session_ordinal: u32) -> u32 {
	if session_ordinal > SECOND_SESSION_ORDINAL {
		return REPEATED_SESSION_FAILURE_UNEXPECTED_THIRD_SESSION
	}
	if session_ordinal < FIRST_SESSION_ORDINAL || repeated_session_active_ordinal() != 0 {
		return REPEATED_SESSION_FAILURE_INVALID_SESSION_ORDINAL
	}
	return next_fixed_user_session_state_failure_code(session_ordinal)
}

next_fixed_user_session_state_failure_code :: proc "contextless" (session_ordinal: u32) -> u32 {
	if repeated_session_completed_count() + 1 != session_ordinal {
		return REPEATED_SESSION_FAILURE_COMPLETED_COUNT
	}
	if repeated_session_total_transition_count() != (session_ordinal - 1) * PER_SESSION_TRANSITION_COUNT {
		return REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT
	}
	return reusable_fixed_user_authority_failure_code()
}

record_completed_fixed_user_session :: proc "contextless" () {
	intrinsics.volatile_store(&repeated_user_session_coordinator.active_session_ordinal, 0)
	intrinsics.volatile_store(&repeated_user_session_coordinator.completed_session_count, repeated_session_completed_count() + 1)
	intrinsics.volatile_store(&repeated_user_session_coordinator.observed_total_transition_count, repeated_session_total_transition_count() + PER_SESSION_TRANSITION_COUNT)
}

completed_session_failure_code :: proc "contextless" (session_ordinal: u32) -> u32 {
	if repeated_session_completed_count() != session_ordinal {
		return REPEATED_SESSION_FAILURE_COMPLETED_COUNT
	}
	if repeated_session_total_transition_count() != session_ordinal * PER_SESSION_TRANSITION_COUNT {
		return REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT
	}
	return completed_session_metadata_failure_code()
}

completed_session_metadata_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_active_ordinal() != 0 || repeated_session_failure() != REPEATED_SESSION_FAILURE_NONE {
		return REPEATED_SESSION_FAILURE_COMPLETED_COUNT
	}
	return REPEATED_SESSION_FAILURE_NONE
}

repeated_session_terminal_failure_code :: proc "contextless" () -> u32 {
	if repeated_session_completed_count() != REQUIRED_SESSION_COUNT {
		return REPEATED_SESSION_FAILURE_COMPLETED_COUNT
	}
	if repeated_session_total_transition_count() != REQUIRED_TOTAL_TRANSITION_COUNT {
		return REPEATED_SESSION_FAILURE_TOTAL_TRANSITION_COUNT
	}
	return repeated_session_terminal_metadata_failure_code()
}

repeated_session_terminal_metadata_failure_code :: proc "contextless" () -> u32 {
	if !repeated_session_header_is_valid() || repeated_session_active_ordinal() != 0 {
		return REPEATED_SESSION_FAILURE_FINAL_VALIDATION
	}
	if repeated_session_failure() != REPEATED_SESSION_FAILURE_NONE || repeated_session_reserved() != 0 {
		return REPEATED_SESSION_FAILURE_FINAL_VALIDATION
	}
	return REPEATED_SESSION_FAILURE_NONE
}

repeated_session_header_is_valid :: proc "contextless" () -> bool {
	return repeated_session_format_version() == REPEATED_SESSION_COORDINATOR_FORMAT_VERSION &&
	       repeated_session_structure_size() == REPEATED_SESSION_COORDINATOR_SIZE &&
	       repeated_session_required_count() == REQUIRED_SESSION_COUNT
}

session_failure_code :: proc "contextless" (session_ordinal: u32) -> u32 {
	if session_ordinal == FIRST_SESSION_ORDINAL {
		return REPEATED_SESSION_FAILURE_FIRST_SESSION
	}
	return REPEATED_SESSION_FAILURE_SECOND_SESSION
}

fail_repeated_user_sessions :: proc "contextless" (failure_code: u32) -> u32 {
	intrinsics.volatile_store(&repeated_user_session_coordinator.active_session_ordinal, 0)
	intrinsics.volatile_store(&repeated_user_session_coordinator.failure_code, failure_code)
	invalidate_fixed_user_session_state()
	return RUNTIME_REPEATED_SESSION_FAILURE
}

set_active_repeated_session_ordinal :: proc "contextless" (session_ordinal: u32) {
	intrinsics.volatile_store(&repeated_user_session_coordinator.active_session_ordinal, session_ordinal)
}

repeated_session_format_version :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.format_version)
}

repeated_session_structure_size :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.structure_size)
}

repeated_session_required_count :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.required_session_count)
}

repeated_session_active_ordinal :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.active_session_ordinal)
}

repeated_session_completed_count :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.completed_session_count)
}

repeated_session_total_transition_count :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.observed_total_transition_count)
}

repeated_session_failure :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.failure_code)
}

repeated_session_reserved :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&repeated_user_session_coordinator.reserved)
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
