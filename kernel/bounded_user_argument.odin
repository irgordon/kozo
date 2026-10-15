package kernel

BOUNDED_USER_ARGUMENT_MAX :: u64(65535)
BOUNDED_USER_ARGUMENT_INCREMENT :: u64(1)
BOUNDED_USER_ARGUMENT_OK :: u32(0)
BOUNDED_USER_ARGUMENT_INVALID :: u32(1)

// The bridge supplies a fixed supervisor-owned result slot, never a user pointer.
@(export)
evaluate_bounded_user_argument :: proc "c" (argument: u64, result: ^u64) -> u32 {
	result^ = 0
	if argument > BOUNDED_USER_ARGUMENT_MAX {
		return BOUNDED_USER_ARGUMENT_INVALID
	}
	result^ = argument + BOUNDED_USER_ARGUMENT_INCREMENT
	return BOUNDED_USER_ARGUMENT_OK
}
