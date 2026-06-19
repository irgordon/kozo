# KOZO Coding Style

Version: 1
Status: Authoritative
Scope: Code construction rules for kernel, userspace, harness, scripts, validators, tests, and generated-code boundaries

---

# 1. Purpose

This document defines how KOZO code is written.

Code should be easy to inspect, easy to change, and difficult to misuse.

Prefer mechanical structure over cleverness.

A reader should understand the primary path before reading defensive paths.

A function should show what it does through its name, inputs, output, and order.

---

# 2. Authority

This document owns coding style.

It does not own:

* system architecture
* security invariants
* ABI contract contents
* syscall semantics
* validation pipeline authority
* compatibility claims
* generated artifact policy

Those belong to higher or separate governance documents.

This document is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, and `docs/CONTRACTS.md`.

For the complete document precedence order, see `docs/GOVERNANCE.md`.

If this document conflicts with invariants, architecture, contract authority, or document precedence, the higher authority wins.

---

# 3. Non-Goals

This document does not define whether KOZO is a microkernel, monolithic kernel, or hybrid kernel.

This document does not define the ABI.

This document does not define syscall behavior.

This document does not define compatibility promises.

This document does not define generated artifact authority.

This document does not make generated reports authoritative.

This document does not replace validator contracts or tests.

---

# 4. Core Principle

Write code that is obvious at the point of use.

A good KOZO function:

* has a clear name
* receives explicit inputs
* returns explicit output
* validates boundary input early
* keeps the normal path flat
* moves details into named helpers
* avoids hidden authority
* avoids hidden allocation
* avoids hidden mutation
* exposes failure through the correct boundary mechanism

Bad code makes the reader reconstruct behavior from scattered helpers, implicit state, or clever expressions.

---

# 5. File Organization

Write files from high level to low level.

Place the main entry point first.

Place orchestration functions next.

Place domain-specific helpers after the functions that use them.

Place small conversion, formatting, parsing, and validation helpers near the bottom.

Good order:

```text
main
run_verification
load_inputs
validate_contracts
build_result
format_diagnostic
parse_status_code
```

Bad order:

```text
parse_status_code
format_diagnostic
main
load_inputs
build_result
run_verification
```

Generated files are not organized manually. Their layout is owned by the generator.

---

# 6. Top-Down Flow

Start with the primary operation.

Move details into named functions.

Do not force the reader to assemble behavior from scattered helpers.

Good:

```python
def validate(self, bundle: dict) -> ValidationResult:
    sources = load_sources(bundle)
    issues = validate_contract(sources)

    return build_result(issues)
```

Bad:

```python
def validate(self, bundle: dict) -> ValidationResult:
    source = Path(bundle["root_dir"], "kernel/main.odin").read_text()
    if "abi.K_OK" in source and "payload.status_bits" in source:
        return ValidationResult(status="pass", code="OK", meta={})
    return ValidationResult(status="fail", code="ERROR", meta={})
```

The first version shows the operation.
The second version hides the contract inside raw matching.

---

# 7. Single Level of Abstraction

Each function should operate at one level of abstraction.

A coordinator function coordinates.

A parser parses.

A matcher matches.

A diagnostic builder builds diagnostics.

Do not mix policy, parsing, matching, source loading, and diagnostic formatting in the same function.

Good:

```python
def validate(self, bundle: dict) -> ValidationResult:
    sources = load_sources(bundle)
    contract = load_contract(bundle)
    issues = validate_sources_against_contract(sources, contract)

    return build_validation_result(issues)
```

Bad:

```python
def validate(self, bundle: dict) -> ValidationResult:
    root = Path(bundle["root_dir"])
    source = (root / "kernel/main.odin").read_text()
    if "case abi.K_SYSCALL_STATUS" not in source:
        return ValidationResult(
            status="fail",
            code="SYSCALL_TABLE_INVALID",
            meta={"reason": "missing_status_branch"},
        )
    return ValidationResult(status="pass", code="OK", meta={})
```

Small validators may remain compact, but they must still separate contract meaning from raw source mechanics.

---

# 8. Simple Over Clever

Prefer obvious code.

Do not compress logic to look sophisticated.

Avoid clever chaining when named steps are clearer.

Good:

```python
registered_validators = load_registered_validators()
missing_tests = find_missing_test_files(registered_validators)

return build_coverage_result(missing_tests)
```

Bad:

```python
return build_coverage_result([v for v in load_registered_validators() if not Path(f"tests/test_{v}.py").exists()])
```

A few extra lines are acceptable when they reveal system meaning.

---

# 9. Fail Early

Check invalid state first.

Return immediately.

Keep the normal path flat.

Good:

```rust
fn handle_status_request(payload: *mut HeartbeatPayload) -> K_STATUS {
    if !payload.is_null() {
        return abi::K_INVALID;
    }

    abi::K_OK
}
```

Bad:

```rust
fn handle_status_request(payload: *mut HeartbeatPayload) -> K_STATUS {
    if payload.is_null() {
        abi::K_OK
    } else {
        abi::K_INVALID
    }
}
```

Guard clauses are preferred when they reduce nesting.

---

# 10. Error Boundaries

Failure behavior must match the boundary.

Startup code may terminate when the program cannot safely continue.

Runtime code must return errors.

Kernel code must return explicit status values unless the failure is unrecoverable.

Validator code must return structured validation failure.

Event-style code must return early.

Optional state must not crash the process.

Good startup boundary:

```rust
fn main() {
    let config = load_config().expect("config load failed");

    run(config).expect("startup failed");
}
```

Good runtime boundary:

```rust
fn handle_request(request: Request) -> Result<Response, Error> {
    let user = load_user(request.user_id)?;

    Ok(build_response(user))
}
```

Good validator boundary:

```python
if missing_fields:
    return fail_result(
        reason="missing_contract_fields",
        contract_field="syscalls.status",
    )
```

Bad runtime boundary:

```rust
fn handle_event(session: Option<Session>) {
    session.unwrap().refresh();
}
```

Use panic only when continuing would be dishonest.

---

# 11. Types Carry Policy

Use types to make invalid states hard to express.

Use specific names for specific states.

Avoid ambiguous booleans that must be interpreted later.

Good:

```rust
struct SyscallId(u32);
struct KernelStatus(u32);

struct NoPayloadSyscall {
    id: SyscallId,
    expected_status: KernelStatus,
}
```

Bad:

```rust
struct Syscall {
    id: u32,
    has_payload: bool,
    valid: bool,
}
```

A type should protect meaning.

---

# 12. Names

Use human-readable names.

Name things by their role in the system.

Avoid abbreviations unless they are common in the domain.

Good:

```python
registered_validator_names = load_registered_validator_names()
missing_negative_markers = find_missing_negative_markers(contract)
```

Bad:

```python
vals = load_vals()
miss = find_bad(contract)
```

Boolean names should read like facts.

Good:

```python
is_report_current = actual_text == expected_text
has_required_validator = validator_name in registered_validators
```

Bad:

```python
current = actual_text == expected_text
validator = validator_name in registered_validators
```

---

# 13. Functions

A function should do one thing.

A function should fit on one screen unless there is a clear reason.

Do not deeply nest functions.

Do not define helper functions inside functions unless they need local closure state and stay small.

Good:

```python
def render_report(inputs: ReportInputs) -> str:
    sections = build_report_sections(inputs)

    return join_sections(sections)


def build_report_sections(inputs: ReportInputs) -> list[str]:
    return [
        render_header(inputs),
        render_summary(inputs),
        render_details(inputs),
    ]
```

Bad:

```python
def render_report(inputs: ReportInputs) -> str:
    def header():
        def title():
            return "# KOZO report"
        return title()

    return header() + "\n" + str(inputs)
```

---

# 14. Conditionals

Prefer guard clauses.

Avoid deeply nested conditionals.

Use named predicates when the condition has meaning.

Good:

```python
if not report_exists(path):
    return missing_report_issue(path)

if not is_report_current(actual, expected):
    return stale_report_issue(path)

return None
```

Bad:

```python
if report_exists(path):
    if is_report_current(actual, expected):
        return None
    else:
        return stale_report_issue(path)
else:
    return missing_report_issue(path)
```

---

# 15. Comments

Use comments sparingly.

Prefer names, types, and structure.

A comment should explain why something exists, not what the code already says.

Good:

```python
# Generated reports are non-authoritative, so the validator compares them
# against rendered contract state instead of trusting checked-in Markdown.
expected_text = render_report(inputs)
```

Bad:

```python
# Render the report.
expected_text = render_report(inputs)
```

Acceptable comments explain constraints, invariants, or non-obvious external behavior.

---

# 16. Python Harness Style

Python harness code must be deterministic.

Harness code must not depend on network access.

Harness code must not depend on wall-clock time unless the value is explicitly passed in as input.

Harness code must not mutate source files unless it is a generator command designed to do so.

Validator rules:

* `validate()` coordinates only.
* Contract definitions must be explicit.
* Raw matching must be isolated in helpers.
* Diagnostics must name the missing or mismatched contract field.
* Validators must fail closed.
* Validators must not silently skip missing evidence.
* Validators must not treat generated artifacts as authoritative over source contracts.
* Every registered validator must have focused tests.
* Every registered validator must have marker-level negative coverage.

Good validator structure:

```python
def validate(self, bundle: dict) -> ValidationResult:
    sources = load_sources(bundle)
    contract = load_contract(bundle)
    issues = validate_contract_against_sources(contract, sources)

    return build_result(issues)
```

Bad validator structure:

```python
def validate(self, bundle: dict) -> ValidationResult:
    source = Path("kernel/main.odin").read_text()
    return "abi.K_OK" in source
```

Python tests must prove failure, not only success.

A negative test must:

* invoke the validator or approved harness path
* provide bad input or bad source state
* assert failure status
* assert diagnostic reason or contract field where practical

---

# 17. Odin Kernel Style

Odin kernel code must be direct and explicit.

Kernel code must not hide authority.

Kernel code must not trust userspace pointers.

Kernel code must not expose kernel object pointers to userspace.

Kernel code must return explicit ABI status values at syscall boundaries.

Kernel syscall handlers must:

* validate syscall identity
* validate pointer/null expectations
* validate request fields before mutation
* mutate only contract-allowed fields
* return declared status values
* keep unknown/default behavior explicit

No hidden allocation is allowed in syscall paths unless documented by a higher authority document.

No global allocator use is allowed unless explicitly documented.

Kernel code must prefer clear branches over clever compression.

Good:

```odin
case abi.K_SYSCALL_STATUS:
    return abi.K_OK
```

Good:

```odin
case abi.K_SYSCALL_DEBUG_HEARTBEAT:
    if payload == nil {
        return abi.K_INVALID
    }

    if payload.sequence != 0xCAFEFEED {
        return abi.K_INVALID
    }

    payload.sequence = 0xCAFEFEEE
    payload.timestamp = 0xDEADBEEF
    payload.status_bits = u32(abi.K_OK)

    return abi.K_OK
```

Bad:

```odin
case 2:
    return 0
```

Syscall selectors must use ABI constants, not hardcoded numeric values.

---

# 18. Rust Userspace Style

Rust userspace code that crosses the KOZO ABI must be explicit.

All kernel-facing Rust code must remain compatible with `no_std` when it belongs to the runtime boundary.

Rust rules:

* prefer `Result` for recoverable runtime failures
* prefer `Option` for absence
* use `let Some(value) = value else { return; };` for event-style early exits
* use `?` when the current function owns the error boundary
* use `expect()` only when continuing would violate startup invariants
* avoid `unwrap()` in runtime paths
* avoid hardcoded syscall numbers
* use generated ABI constants
* use null payload only for no-payload syscalls that declare it
* validate returned status where the contract requires it

Good:

```rust
fn status_request() -> abi::K_STATUS {
    let status = invoke_no_payload_bridge(abi::K_SYSCALL_STATUS);

    validate_status_return_status(status)
}
```

Bad:

```rust
fn status_request() -> abi::K_STATUS {
    unsafe { syscall_entry(2, core::ptr::null_mut()) }
}
```

Generated ABI warnings must not be fixed by editing generated bindings directly.

---

# 19. Shell Script Style

Shell scripts must use strict mode:

```bash
set -euo pipefail
```

Shell scripts must:

* check required commands before use
* check required files before use
* write generated artifacts predictably
* clean transient outputs
* fail closed on missing proof tools
* print failing command logs on failure
* avoid hidden dependency on current working directory

Good:

```bash
need_cmd python3
need_cmd odin
need_cmd cargo
need_cmd nm
```

Generated proof artifacts should be written atomically when practical.

Temporary files must be cleaned on exit.

---

# 20. Test Style

Tests must prove behavior and failure.

A test suite must include:

* positive path
* negative path
* diagnostic quality where applicable
* stale or drift case for generated reports
* source mismatch case for validators

A negative test that only contains a failure-like name is not enough.

Good:

```python
def test_missing_report_file_fails(self):
    remove_report_file()

    result = AbiSurfaceReportValidator().validate(bundle)

    self.assertEqual(result.status, "fail")
    self.assertEqual(result.meta["reason"], "missing_report_file")
```

Bad:

```python
def test_missing_report_file_fails(self):
    pass
```

Every focused validator test file must include `KOZO_NEGATIVE_COVERAGE`.

---

# 21. Generated File Style

Generated files must not be edited manually.

Generated reports are review surfaces, not sources of truth.

Generated bindings are ABI outputs, not hand-written policy.

A generated file must have:

* a source of truth
* a generator
* a validator or drift check
* a refresh command

Generated Markdown must clearly state that it is generated and non-authoritative.

---

# 22. Diagnostics

Diagnostics must name the thing that failed.

A good diagnostic includes:

* reason
* contract field
* validator name where applicable
* expected value when useful
* actual value when useful

Good:

```python
{
    "reason": "missing_syscall_constant",
    "contract_field": "constants.syscalls.K_SYSCALL_STATUS",
}
```

Bad:

```python
{
    "reason": "bad",
}
```

Diagnostics are part of the operator interface. They must be precise.

---

# 23. Liskov Substitution and Interface Safety

Implementations must be safely usable wherever their interface is expected.

Do not strengthen preconditions in an implementation.

Do not weaken guarantees in an implementation.

Do not add surprise failure modes.

If an implementation has narrower rules, represent that with a narrower interface.

Good:

```python
class Validator:
    def validate(self, bundle: dict) -> ValidationResult:
        raise NotImplementedError
```

Every validator must return a `ValidationResult`.

Bad:

```python
class SpecialValidator(Validator):
    def validate(self, bundle: dict) -> bool:
        return True
```

Interface boundaries must remain predictable.

---

# 24. Code Review Checklist

Before merging code, verify:

* the primary path is easy to read
* invalid states are checked early
* no hidden authority was added
* no generated file was manually edited
* no hardcoded ABI value replaced a generated constant
* validators have focused negative coverage
* diagnostics name contract fields
* runtime behavior matches contract behavior
* tests prove both success and failure
* comments explain why, not what
* verification passes

---

# 25. Relationship to Other Governance Documents

`GOVERNANCE.md` owns precedence.

`INVARIANTS.md` owns non-negotiable truths.

`ARCHITECTURE.md` owns system structure.

`CONTRACTS.md` owns contract authority.

`VALIDATION.md` owns verification requirements.

`GENERATED_ARTIFACTS.md` owns generated-file policy.

This document only explains how code should be written inside those boundaries.

---

# 26. Summary

Write code top down.

Keep the primary path flat.

Prefer simple names and explicit types.

Return early on invalid state.

Return recoverable errors.

Panic only when continuing would be dishonest.

Use generated ABI constants instead of hardcoded values.

Keep validators contract-driven.

Keep generated files non-authoritative.

Use comments only when structure cannot carry the reason.
