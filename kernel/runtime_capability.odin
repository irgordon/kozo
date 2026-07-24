package kernel

RUNTIME_STATUS_REQUEST_VERSION :: u32(1)
RUNTIME_STATUS_RESPONSE_VERSION :: u32(1)
RUNTIME_STATUS_QUERY_CAPABILITY_ID :: u32(1)
RUNTIME_STATUS_SUPPORTED_FLAGS :: u32(0)

RUNTIME_STATUS_REQUEST_SIZE :: uintptr(16)
RUNTIME_STATUS_REQUEST_ALIGNMENT :: uintptr(4)
RUNTIME_STATUS_RESPONSE_SIZE :: uintptr(64)
RUNTIME_STATUS_RESPONSE_ALIGNMENT :: uintptr(8)

RUNTIME_STAGE_CONTROLLED_RUNTIME_LOOP :: u32(5)
RUNTIME_PROVEN_STAGE_MASK :: u64(0x3f)

RUNTIME_CAPABILITY_INVALID_REQUEST_POINTER :: u32(9)
RUNTIME_CAPABILITY_INVALID_RESPONSE_POINTER :: u32(10)
RUNTIME_CAPABILITY_UNSUPPORTED_REQUEST_VERSION :: u32(11)
RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY :: u32(12)
RUNTIME_CAPABILITY_UNSUPPORTED_FLAGS :: u32(13)
RUNTIME_CAPABILITY_INVALID_RESERVED_FIELD :: u32(14)
RUNTIME_CAPABILITY_RESPONSE_VALIDATION_FAILURE :: u32(15)
RUNTIME_CAPABILITY_EXECUTION_FAILURE :: u32(16)

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

#assert(size_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_SIZE)
#assert(align_of(Runtime_Status_Request) == RUNTIME_STATUS_REQUEST_ALIGNMENT)
#assert(size_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_SIZE)
#assert(align_of(Runtime_Status_Response) == RUNTIME_STATUS_RESPONSE_ALIGNMENT)

@(export)
execute_first_governed_capability :: proc "contextless" () -> u32 {
	request := Runtime_Status_Request{
		version = RUNTIME_STATUS_REQUEST_VERSION,
		capability_id = RUNTIME_STATUS_QUERY_CAPABILITY_ID,
		flags = RUNTIME_STATUS_SUPPORTED_FLAGS,
		reserved = 0,
	}
	response := Runtime_Status_Response{}
	status := dispatch_runtime_capability(&request, &response)
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
dispatch_runtime_capability :: proc "contextless" (
	request: ^Runtime_Status_Request,
	response: ^Runtime_Status_Response,
) -> u32 {
	validation_status := validate_runtime_status_request(request, response)
	if validation_status != RUNTIME_PROGRESSION_OK {
		return validation_status
	}
	clear_runtime_status_response(response)
	runtime_serial_write_capability_dispatch_marker()
	switch request.capability_id {
	case RUNTIME_STATUS_QUERY_CAPABILITY_ID:
		return query_runtime_status(response)
	case:
		return RUNTIME_CAPABILITY_UNSUPPORTED_CAPABILITY
	}
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
	return first_start < second_start + second_size &&
	       second_start < first_start + first_size
}

clear_runtime_status_response :: proc "contextless" (response: ^Runtime_Status_Response) {
	response^ = Runtime_Status_Response{}
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
