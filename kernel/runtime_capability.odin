package kernel

import "base:intrinsics"

RUNTIME_STATUS_REQUEST_VERSION :: u32(1)
RUNTIME_STATUS_RESPONSE_VERSION :: u32(1)
RUNTIME_STATUS_QUERY_CAPABILITY_ID :: u32(1)
RUNTIME_STATUS_SUPPORTED_FLAGS :: u32(0)

RUNTIME_STATE_TRANSITION_REQUEST_VERSION :: u32(1)
RUNTIME_STATE_TRANSITION_RESPONSE_VERSION :: u32(1)
RUNTIME_STATE_TRANSITION_CAPABILITY_ID :: u32(2)
RUNTIME_STATE_TRANSITION_SUPPORTED_FLAGS :: u32(0)

RUNTIME_STATUS_REQUEST_SIZE :: uintptr(16)
RUNTIME_STATUS_REQUEST_ALIGNMENT :: uintptr(4)
RUNTIME_STATUS_RESPONSE_SIZE :: uintptr(64)
RUNTIME_STATUS_RESPONSE_ALIGNMENT :: uintptr(8)

RUNTIME_STATE_TRANSITION_REQUEST_SIZE :: uintptr(32)
RUNTIME_STATE_TRANSITION_REQUEST_ALIGNMENT :: uintptr(8)
RUNTIME_STATE_TRANSITION_RESPONSE_SIZE :: uintptr(48)
RUNTIME_STATE_TRANSITION_RESPONSE_ALIGNMENT :: uintptr(8)
RUNTIME_STATE_CELL_SIZE :: uintptr(16)
RUNTIME_STATE_CELL_ALIGNMENT :: uintptr(8)

RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP :: u32(5)
RUNTIME_PROVEN_STAGE_MASK :: u64(0x3f)

RUNTIME_STATE_READY :: u32(1)
RUNTIME_STATE_ACTIVE :: u32(2)
RUNTIME_STATE_INITIAL_GENERATION :: u64(0)
RUNTIME_STATE_TERMINAL_GENERATION :: u64(1)
RUNTIME_STATE_MAX_GENERATION :: u64(0xffffffffffffffff)

RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER :: u32(9)
RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER :: u32(10)
RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION :: u32(11)
RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY :: u32(12)
RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS :: u32(13)
RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD :: u32(14)
RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE :: u32(15)
RUNTIME_CAPABILITY_EXECUTION_FAILURE :: u32(16)
RUNTIME_STATE_STALE_GENERATION :: u32(17)
RUNTIME_STATE_INVALID_TRANSITION :: u32(18)
RUNTIME_STATE_READBACK_FAILED :: u32(19)

Runtime_Capability_Header :: struct {
	version:       u32,
	capability_id: u32,
}

Runtime_Status_Request :: struct {
	version:       u32,
	capability_id: u32,
	flags:         u32,
	reserved:      u32,
}

Runtime_Status_Response :: struct {
	version:                         u32,
	capability_id:                   u32,
	status:                          u32,
	current_progression_stage:       u32,
	proven_stage_mask:               u64,
	boot_memory_region_size:         u64,
	controlled_loop_iteration_limit: u64,
	controlled_loop_final_count:     u64,
	controlled_loop_accumulator:     u64,
	reserved:                        u64,
}

Runtime_State_Cell :: struct {
	state:      u32,
	reserved:   u32,
	generation: u64,
}

Runtime_State_Transition_Request :: struct {
	version:             u32,
	capability_id:       u32,
	expected_state:      u32,
	requested_state:     u32,
	expected_generation: u64,
	flags:               u32,
	reserved:            u32,
}

Runtime_State_Transition_Response :: struct {
	version:             u32,
	capability_id:       u32,
	status:              u32,
	previous_state:      u32,
	current_state:       u32,
	reserved_0:          u32,
	previous_generation: u64,
	current_generation:  u64,
	reserved_1:          u64,
}

#assert(size_of(Runtime_Capability_Header) == 8)
#assert(align_of(Runtime_Capability_Header) == 4)
#assert(size_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_SIZE)
#assert(align_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_ALIGNMENT)
#assert(size_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_SIZE)
#assert(align_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_ALIGNMENT)
#assert(size_of(Runtime_State_Cell) == RUNTIME_STATE_CELL_SIZE)
#assert(align_of(Runtime_State_Cell) == RUNTIME_STATE_CELL_ALIGNMENT)
#assert(size_of(Runtime_State_Transition_Request) == RUNTIME_STATE_TRANSITION_REQUEST_SIZE)
#assert(align_of(Runtime_State_Transition_Request) == RUNTIME_STATE_TRANSITION_REQUEST_ALIGNMENT)
#assert(size_of(Runtime_State_Transition_Response) == RUNTIME_STATE_TRANSITION_RESPONSE_SIZE)
#assert(align_of(Runtime_State_Transition_Response) == RUNTIME_STATE_TRANSITION_RESPONSE_ALIGNMENT)

@(export)
runtime_state_transition_cell: Runtime_State_Cell

@(export)
initialize_runtime_state_transition_cell :: proc "contextless" () -> bool {
	runtime_state_cell_store(RUNTIME_STATE_READY, RUNTIME_STATE_INITIAL_GENERATION)
	intrinsics.volatile_store(&runtime_state_transition_cell.reserved, 0)
	return runtime_state_cell_is_ready()
}

@(export)
execute_first_governed_capability :: proc "contextless" () -> u32 {
	request := Runtime_Status_Request{
		version = RUNTIME_STATUS_REQUEST_VERSION,
		capability_id = RUNTIME_STATUS_QUERY_CAPABILITY_ID,
		flags = RUNTIME_STATUS_SUPPORTED_FLAGS,
		reserved = 0,
	}
	response: Runtime_Status_Response = ---
	status := dispatch_runtime_capability(cast(rawptr)(&request), cast(rawptr)(&response))
	if status != RUNTIME_PROGRESSION_OK {
		return status
	}
	if !validate_runtime_status_response(&response) {
		return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE
	}
	runtime_serial_write_first_capability_marker()
	return RUNTIME_PROGRESSION_OK
}

@(export)
execute_second_governed_capability :: proc "contextless" () -> u32 {
	request := governed_runtime_state_transition_request()
	response: Runtime_State_Transition_Response = ---
	status := dispatch_runtime_capability(cast(rawptr)(&request), cast(rawptr)(&response))
	if status != RUNTIME_PROGRESSION_OK {
		return status
	}
	if !validate_runtime_state_transition_response(&response) {
		return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE
	}
	runtime_serial_write_second_capability_marker()
	return RUNTIME_PROGRESSION_OK
}

governed_runtime_state_transition_request :: proc "contextless" () -> Runtime_State_Transition_Request {
	return Runtime_State_Transition_Request{
		version = RUNTIME_STATE_TRANSITION_REQUEST_VERSION,
		capability_id = RUNTIME_STATE_TRANSITION_CAPABILITY_ID,
		expected_state = RUNTIME_STATE_READY,
		requested_state = RUNTIME_STATE_ACTIVE,
		expected_generation = RUNTIME_STATE_INITIAL_GENERATION,
		flags = RUNTIME_STATE_TRANSITION_SUPPORTED_FLAGS,
		reserved = 0,
	}
}

@(export)
dispatch_runtime_capability :: proc "contextless" (
	request: rawptr,
	response: rawptr,
) -> u32 {
	header_status := validate_runtime_capability_header(request)
	if header_status != RUNTIME_PROGRESSION_OK {
		return header_status
	}
	header := cast(^Runtime_Capability_Header)(request)
	switch header.capability_id {
	case RUNTIME_STATUS_QUERY_CAPABILITY_ID:
		return dispatch_runtime_status_query(
			cast(^Runtime_Status_Request)(request),
			cast(^Runtime_Status_Response)(response),
		)
	case RUNTIME_STATE_TRANSITION_CAPABILITY_ID:
		return dispatch_runtime_state_transition(
			cast(^Runtime_State_Transition_Request)(request),
			cast(^Runtime_State_Transition_Response)(response),
		)
	case:
		return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY
	}
}

validate_runtime_capability_header :: proc "contextless" (request: rawptr) -> u32 {
	if request == nil || uintptr(request) % align_of(Runtime_Capability_Header) != 0 {
		return RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER
	}
	return RUNTIME_PROGRESSION_OK
}

dispatch_runtime_status_query :: proc "contextless" (
	request: ^Runtime_Status_Request,
	response: ^Runtime_Status_Response,
) -> u32 {
	validation_status := validate_runtime_status_request(request, response)
	if validation_status != RUNTIME_PROGRESSION_OK {
		return validation_status
	}
	clear_runtime_status_response(response)
	runtime_serial_write_capability_dispatch_marker()
	return query_runtime_status(response)
}

validate_runtime_status_request :: proc "contextless" (
	request: ^Runtime_Status_Request,
	response: ^Runtime_Status_Response,
) -> u32 {
	if request == nil || uintptr(request) % RUNTIME_STATUS_REQUEST_ALIGNMENT != 0 {
		return RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER
	}
	if !runtime_status_response_pointer_is_valid(request, response) {
		return RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER
	}
	if request.version != RUNTIME_STATUS_REQUEST_VERSION {
		return RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION
	}
	if request.capability_id != RUNTIME_STATUS_QUERY_CAPABILITY_ID {
		return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY
	}
	if request.flags != RUNTIME_STATUS_SUPPORTED_FLAGS {
		return RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS
	}
	if request.reserved != 0 {
		return RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD
	}
	return RUNTIME_PROGRESSION_OK
}

runtime_status_response_pointer_is_valid :: proc "contextless" (
	request: ^Runtime_Status_Request,
	response: ^Runtime_Status_Response,
) -> bool {
	if response == nil || uintptr(response) % RUNTIME_STATUS_RESPONSE_ALIGNMENT != 0 {
		return false
	}
	return !memory_ranges_overlap(
		uintptr(request),
		RUNTIME_STATUS_REQUEST_SIZE,
		uintptr(response),
		RUNTIME_STATUS_RESPONSE_SIZE,
	)
}

memory_ranges_overlap :: proc "contextless" (
	first_start, first_size, second_start, second_size: uintptr,
) -> bool {
	if first_start <= second_start {
		return second_start - first_start < first_size
	}
	return first_start - second_start < second_size
}

clear_runtime_status_response :: proc "contextless" (response: ^Runtime_Status_Response) {
	response.version = 0
	response.capability_id = 0
	response.status = 0
	response.current_progression_stage = 0
	response.proven_stage_mask = 0
	response.boot_memory_region_size = 0
	response.controlled_loop_iteration_limit = 0
	response.controlled_loop_final_count = 0
	response.controlled_loop_accumulator = 0
	response.reserved = 0
}

@(export)
query_runtime_status :: proc "contextless" (response: ^Runtime_Status_Response) -> u32 {
	if !controlled_runtime_loop_state_is_complete() {
		return RUNTIME_CAPABILITY_EXECUTION_FAILURE
	}
	populate_runtime_status_response(response)
	if !validate_runtime_status_response(response) {
		return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE
	}
	runtime_serial_write_status_query_marker()
	return RUNTIME_PROGRESSION_OK
}

controlled_runtime_loop_state_is_complete :: proc "contextless" () -> bool {
	return runtime_loop_limit() == RUNTIME_LOOP_ITERATION_LIMIT &&
	       runtime_loop_iteration_count() == RUNTIME_LOOP_ITERATION_LIMIT &&
	       runtime_loop_accumulator() == RUNTIME_LOOP_EXPECTED_ACCUMULATOR &&
	       runtime_loop_status() == RUNTIME_LOOP_STATUS_COMPLETED &&
	       runtime_loop_reserved() == 0
}

populate_runtime_status_response :: proc "contextless" (response: ^Runtime_Status_Response) {
	response.version = RUNTIME_STATUS_RESPONSE_VERSION
	response.capability_id = RUNTIME_STATUS_QUERY_CAPABILITY_ID
	response.status = RUNTIME_PROGRESSION_OK
	response.current_progression_stage = RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP
	response.proven_stage_mask = RUNTIME_PROVEN_STAGE_MASK
	response.boot_memory_region_size = RUNTIME_BOOT_MEMORY_SIZE
	response.controlled_loop_iteration_limit = runtime_loop_limit()
	response.controlled_loop_final_count = runtime_loop_iteration_count()
	response.controlled_loop_accumulator = runtime_loop_accumulator()
	response.reserved = 0
}

validate_runtime_status_response :: proc "contextless" (
	response: ^Runtime_Status_Response,
) -> bool {
	if response == nil || uintptr(response) % RUNTIME_STATUS_RESPONSE_ALIGNMENT != 0 {
		return false
	}
	return response.version == RUNTIME_STATUS_RESPONSE_VERSION &&
	       response.capability_id == RUNTIME_STATUS_QUERY_CAPABILITY_ID &&
	       response.status == RUNTIME_PROGRESSION_OK &&
	       response.current_progression_stage == RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP &&
	       response.proven_stage_mask == RUNTIME_PROVEN_STAGE_MASK &&
	       response.boot_memory_region_size == RUNTIME_BOOT_MEMORY_SIZE &&
	       response.controlled_loop_iteration_limit == RUNTIME_LOOP_ITERATION_LIMIT &&
	       response.controlled_loop_final_count == RUNTIME_LOOP_ITERATION_LIMIT &&
	       response.controlled_loop_accumulator == RUNTIME_LOOP_EXPECTED_ACCUMULATOR &&
	       response.reserved == 0
}

@(export)
dispatch_runtime_state_transition :: proc "contextless" (
	request: ^Runtime_State_Transition_Request,
	response: ^Runtime_State_Transition_Response,
) -> u32 {
	validation_status := validate_runtime_state_transition_request(request, response)
	if validation_status != RUNTIME_PROGRESSION_OK {
		return validation_status
	}
	clear_runtime_state_transition_response(response)
	return transition_runtime_state(request, response)
}

validate_runtime_state_transition_request :: proc "contextless" (
	request: ^Runtime_State_Transition_Request,
	response: ^Runtime_State_Transition_Response,
) -> u32 {
	if request == nil || uintptr(request) % RUNTIME_STATE_TRANSITION_REQUEST_ALIGNMENT != 0 {
		return RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER
	}
	if !runtime_state_transition_response_pointer_is_valid(request, response) {
		return RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER
	}
	if request.version != RUNTIME_STATE_TRANSITION_REQUEST_VERSION {
		return RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION
	}
	if request.capability_id != RUNTIME_STATE_TRANSITION_CAPABILITY_ID {
		return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY
	}
	if request.flags != RUNTIME_STATE_TRANSITION_SUPPORTED_FLAGS {
		return RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS
	}
	if request.reserved != 0 {
		return RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD
	}
	if request.expected_generation != RUNTIME_STATE_INITIAL_GENERATION {
		return RUNTIME_STATE_STALE_GENERATION
	}
	if request.expected_state != RUNTIME_STATE_READY ||
	   request.requested_state != RUNTIME_STATE_ACTIVE {
		return RUNTIME_STATE_INVALID_TRANSITION
	}
	return RUNTIME_PROGRESSION_OK
}

runtime_state_transition_response_pointer_is_valid :: proc "contextless" (
	request: ^Runtime_State_Transition_Request,
	response: ^Runtime_State_Transition_Response,
) -> bool {
	if response == nil || uintptr(response) % RUNTIME_STATE_TRANSITION_RESPONSE_ALIGNMENT != 0 {
		return false
	}
	return !memory_ranges_overlap(
		uintptr(request),
		RUNTIME_STATE_TRANSITION_REQUEST_SIZE,
		uintptr(response),
		RUNTIME_STATE_TRANSITION_RESPONSE_SIZE,
	)
}

clear_runtime_state_transition_response :: proc "contextless" (
	response: ^Runtime_State_Transition_Response,
) {
	response.version = 0
	response.capability_id = 0
	response.status = 0
	response.previous_state = 0
	response.current_state = 0
	response.reserved_0 = 0
	response.previous_generation = 0
	response.current_generation = 0
	response.reserved_1 = 0
}

@(export)
transition_runtime_state :: proc "contextless" (
	request: ^Runtime_State_Transition_Request,
	response: ^Runtime_State_Transition_Response,
) -> u32 {
	previous_state := runtime_state_cell_state()
	previous_generation := runtime_state_cell_generation()
	transition_status := validate_current_runtime_state(
		request,
		previous_state,
		previous_generation,
	)
	if transition_status != RUNTIME_PROGRESSION_OK {
		return transition_status
	}
	runtime_serial_write_state_update_enter_marker()
	runtime_state_cell_store(RUNTIME_STATE_ACTIVE, RUNTIME_STATE_TERMINAL_GENERATION)
	if !runtime_state_cell_is_active() {
		runtime_state_cell_store(previous_state, previous_generation)
		return RUNTIME_STATE_READBACK_FAILED
	}
	populate_runtime_state_transition_response(response, previous_state, previous_generation)
	if !validate_runtime_state_transition_response(response) {
		return RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE
	}
	runtime_serial_write_state_update_ok_marker()
	return RUNTIME_PROGRESSION_OK
}

validate_current_runtime_state :: proc "contextless" (
	request: ^Runtime_State_Transition_Request,
	observed_state: u32,
	observed_generation: u64,
) -> u32 {
	if observed_state != RUNTIME_STATE_READY ||
	   runtime_state_cell_reserved() != 0 {
		return RUNTIME_STATE_INVALID_TRANSITION
	}
	if observed_generation == RUNTIME_STATE_MAX_GENERATION ||
	   observed_generation != request.expected_generation {
		return RUNTIME_STATE_STALE_GENERATION
	}
	return RUNTIME_PROGRESSION_OK
}

populate_runtime_state_transition_response :: proc "contextless" (
	response: ^Runtime_State_Transition_Response,
	previous_state: u32,
	previous_generation: u64,
) {
	response.version = RUNTIME_STATE_TRANSITION_RESPONSE_VERSION
	response.capability_id = RUNTIME_STATE_TRANSITION_CAPABILITY_ID
	response.status = RUNTIME_PROGRESSION_OK
	response.previous_state = previous_state
	response.current_state = runtime_state_cell_state()
	response.reserved_0 = 0
	response.previous_generation = previous_generation
	response.current_generation = runtime_state_cell_generation()
	response.reserved_1 = 0
}

validate_runtime_state_transition_response :: proc "contextless" (
	response: ^Runtime_State_Transition_Response,
) -> bool {
	if response == nil || uintptr(response) % RUNTIME_STATE_TRANSITION_RESPONSE_ALIGNMENT != 0 {
		return false
	}
	return response.version == RUNTIME_STATE_TRANSITION_RESPONSE_VERSION &&
	       response.capability_id == RUNTIME_STATE_TRANSITION_CAPABILITY_ID &&
	       response.status == RUNTIME_PROGRESSION_OK &&
	       response.previous_state == RUNTIME_STATE_READY &&
	       response.current_state == RUNTIME_STATE_ACTIVE &&
	       response.reserved_0 == 0 &&
	       response.previous_generation == RUNTIME_STATE_INITIAL_GENERATION &&
	       response.current_generation == RUNTIME_STATE_TERMINAL_GENERATION &&
	       response.reserved_1 == 0
}

runtime_state_cell_is_ready :: proc "contextless" () -> bool {
	return runtime_state_cell_state() == RUNTIME_STATE_READY &&
	       runtime_state_cell_reserved() == 0 &&
	       runtime_state_cell_generation() == RUNTIME_STATE_INITIAL_GENERATION
}

runtime_state_cell_is_active :: proc "contextless" () -> bool {
	return runtime_state_cell_state() == RUNTIME_STATE_ACTIVE &&
	       runtime_state_cell_reserved() == 0 &&
	       runtime_state_cell_generation() == RUNTIME_STATE_TERMINAL_GENERATION
}

@(export)
runtime_state_cell_store :: proc "contextless" (state: u32, generation: u64) {
	// Volatile stores and later loads preserve the bounded mutation evidence.
	intrinsics.volatile_store(&runtime_state_transition_cell.state, state)
	intrinsics.volatile_store(&runtime_state_transition_cell.generation, generation)
}

@(export)
runtime_state_cell_state :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&runtime_state_transition_cell.state)
}

@(export)
runtime_state_cell_reserved :: proc "contextless" () -> u32 {
	return intrinsics.volatile_load(&runtime_state_transition_cell.reserved)
}

@(export)
runtime_state_cell_generation :: proc "contextless" () -> u64 {
	return intrinsics.volatile_load(&runtime_state_transition_cell.generation)
}
