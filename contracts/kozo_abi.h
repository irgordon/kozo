#ifndef KOZO_ABI_H
#define KOZO_ABI_H

#include <stdint.h>

#define KOZO_ABI_VERSION 1

typedef uint64_t kozo_handle_t;

typedef enum k_status_t {
	K_OK = 0,
	K_INVALID = 1,
	K_DENIED = 2,
} k_status_t;

typedef enum k_syscall_id_t {
	K_SYSCALL_NOP = 0,
	K_SYSCALL_DEBUG_HEARTBEAT = 1,
} k_syscall_id_t;

typedef struct k_heartbeat_payload_t {
	uint64_t sequence;
	uint64_t timestamp;
	uint32_t status_bits;
} k_heartbeat_payload_t;

#endif
