# KOZO Runtime Capabilities

Version: 1
Status: Active
Scope: Governed internal runtime capabilities

---

# 1. Authority

Capability-specific contracts under `contracts/` own capability identity,
geometry, behavior, evidence, and claim boundaries. This document is
descriptive and does not override those contracts.

Runtime capability requests are constructed by KOZO kernel code and execute in
the same kernel address space. They are not a userspace ABI, hardware syscall
surface, authentication boundary, authorization boundary, or privilege
boundary.

# 2. Direct Dispatch

KOZO uses one direct dispatcher:

```text
capability ID 1 -> RUNTIME_STATUS_QUERY
capability ID 2 -> RUNTIME_STATE_TRANSITION
other           -> unsupported capability
```

Capability ID 1 retains ownership of the single generic
`KOZO_CAPABILITY_DISPATCH_ENTER` marker. Capability ID 2 has fixed,
capability-specific markers and does not repeat the generic marker.

# 3. Runtime Status Query

`contracts/first_governed_runtime_capability.v0.json` governs capability ID 1.
It uses a versioned 16-byte request aligned to 4 bytes and a versioned 64-byte
response aligned to 8 bytes. It reports the accepted controlled-runtime stage
state without mutating the governed runtime state cell.

# 4. Runtime State Transition

`contracts/runtime_state_transition_capability.v0.json` governs capability ID
2. Its fixed geometry is:

| Object | Size | Alignment | Ownership |
| --- | ---: | ---: | --- |
| Request | 32 bytes | 8 bytes | Kernel-constructed stack value |
| Response | 48 bytes | 8 bytes | Kernel-constructed stack value |
| State cell | 16 bytes | 8 bytes | Boot-owned static storage |

The only permitted transition is:

```text
READY, generation 0
-> ACTIVE, generation 1
```

The request must identify capability ID 2, version 1, expected state READY,
requested state ACTIVE, expected generation 0, flags 0, and reserved fields 0.
Pointer alignment, overflow-safe range geometry, and request/response
non-overlap are validated before mutation.

All evidence-bearing state and generation accesses are volatile. The handler
reads and validates the current value, emits
`KOZO_RUNTIME_STATE_UPDATE_ENTER`, writes ACTIVE/1, reads it back, populates
and validates the response, then emits `KOZO_RUNTIME_STATE_UPDATE_OK`. A
readback mismatch restores the previous state and generation and returns the
governed failure status. `KOZO_SECOND_CAPABILITY_OK` is emitted only after the
coordinator validates the response.

# 5. Marker Ownership

The governed capability suffix is:

```text
KOZO_CAPABILITY_DISPATCH_ENTER
KOZO_RUNTIME_STATUS_QUERY_OK
KOZO_FIRST_CAPABILITY_OK
KOZO_RUNTIME_STATE_UPDATE_ENTER
KOZO_RUNTIME_STATE_UPDATE_OK
KOZO_SECOND_CAPABILITY_OK
KOZO_RUNTIME_RETURN_OK
```

Executed Odin code invokes fixed assembly bridges for these markers. Scripts,
validators, and metadata generators do not emit runtime success markers.

# 6. Status and Failure Behavior

Capability ID 2 preserves the existing capability statuses 0 and 9 through 16
and adds:

```text
17 -> stale generation
18 -> invalid transition
19 -> state readback failure
```

Unknown capability IDs fail without mutation. Invalid requests, invalid
geometry, stale generations, invalid transitions, failed readback, invalid
responses, and nonzero capability status prevent the governed runtime return
marker. All failure paths converge on the existing terminal halt path.

# 7. Claim Boundary

The state-transition capability proves one kernel-constructed, bounded,
versioned request can transition one boot-owned state cell from READY/0 to
ACTIVE/1 with volatile readback and a validated fixed response.

It does not prove arbitrary kernel memory writes, a general state-machine
framework, dynamic capability registration, concurrent or atomic execution,
persistent state, userspace access, authentication, authorization, privilege
separation, process isolation, hardware syscall entry, compatibility, or
production readiness.

# 8. Paging Prerequisite

v0.8.3 establishes the fixed user-mapping foundation before Odin runtime
progression. It does not add a new capability ID and does not change either
capability request, response, state, or dispatch behavior. Both capabilities
execute only after table policy, CR3 readback, and mapping survival succeed.
The mappings are future privilege-probe prerequisites, not proof of Ring 3 or
general userspace.

# 9. Privilege Probe Ordering

v0.8.4 executes the fixed privilege-transition probe after mapping survival
and before `KOZO_RUNTIME_PROGRESS_ENTRY`. It does not add a capability ID,
change capability request or response geometry, or expose either internal
capability to CPL3. Both capabilities still execute in Odin at CPL0 only after
the fixed CPL3 round trip returns through its governed continuation.
