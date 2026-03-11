# KOZO System Architecture Overview

```
                                     KOZO SYSTEM
                         Deterministic Agentic Execution Protocol
────────────────────────────────────────────────────────────────────────────────


                         ┌─────────────────────────────────┐
                         │        Semantic Registry        │
                         │        harness/registry.py      │
                         │                                 │
                         │  • SUBSYSTEMS                   │
                         │  • CODES                        │
                         │  • CHECKS (validator order)     │
                         │  • STATUSES                     │
                         │  • ARTIFACT_VERSION             │
                         └──────────────┬──────────────────┘
                                        │
                                        │
                         ┌──────────────▼──────────────────┐
                         │       Structural Registry        │
                         │       harness/invariants.py      │
                         │                                  │
                         │  • nonempty_string_list          │
                         │  • string_list                   │
                         │  • verification_ref              │
                         │                                  │
                         │  predicates + schema fragments   │
                         └──────────────┬───────────────────┘
                                        │
                                        │
                        ┌───────────────▼─────────────────┐
                        │        Schema Generators         │
                        │                                  │
                        │  schema_gen.py                   │
                        │  schema_gen_agent_context.py     │
                        └───────────────┬─────────────────┘
                                        │
                                        ▼

                   ┌─────────────────────────────────────────────┐
                   │                SCHEMAS                      │
                   │                                             │
                   │  todo.schema.json                           │
                   │  runtime.schema.json                        │
                   │  latest_verify.schema.json                  │
                   │  agent_context.schema.json                  │
                   │  subagent.schema.json                       │
                   │  lessons.schema.json                        │
                   └───────────────┬─────────────────────────────┘
                                   │
                                   │
                                   ▼

══════════════════════════════════════════════════════════════════════
                        HARNESS EXECUTION PIPELINE
══════════════════════════════════════════════════════════════════════


           ┌────────────────────────────────────────────────┐
           │                    verify.sh                    │
           │                                                │
           │  orchestrates verification pipeline            │
           └───────────────┬────────────────────────────────┘
                           │
                           ▼

           ┌────────────────────────────────────────────────┐
           │                VALIDATOR PIPELINE               │
           │                                                │
           │  schema                                        │
           │  plan_lifecycle                                │
           │  step_scope                                    │
           │  verification_refs                             │
           │  explanation                                   │
           │  preconditions                                 │
           │  subagent                                      │
           │  rust                                          │
           │  odin                                          │
           │  abi                                           │
           │  evidence                                      │
           │                                                │
           │  (pure deterministic validators)               │
           └───────────────┬────────────────────────────────┘
                           │
                           ▼

           ┌────────────────────────────────────────────────┐
           │                aggregator.py                    │
           │                                                │
           │  deterministic reducer                         │
           │                                                │
           │  produces                                      │
           │  artifacts/latest_verify.json                  │
           └───────────────┬────────────────────────────────┘
                           │
                           ▼

           ┌────────────────────────────────────────────────┐
           │                summarize.py                     │
           │                                                │
           │  inputs                                        │
           │      todo.json                                 │
           │      runtime.json                              │
           │      latest_verify.json                        │
           │                                                │
           │  output                                        │
           │      agent_context.json                        │
           └───────────────┬────────────────────────────────┘
                           │
                           ▼


══════════════════════════════════════════════════════════════════════
                             CONTROL PLANE
══════════════════════════════════════════════════════════════════════


                ┌─────────────────────────────────────┐
                │             ARTIFACTS               │
                │                                     │
                │  tasks/todo.json                    │
                │  tasks/runtime.json                 │
                │  artifacts/latest_verify.json       │
                │  agent/agent_context.json           │
                └──────────────┬──────────────────────┘
                               │
                               ▼


══════════════════════════════════════════════════════════════════════
                              AGENT LOOP
══════════════════════════════════════════════════════════════════════


                        ┌─────────────────────┐
                        │        AGENT        │
                        │                     │
                        │ reads               │
                        │ agent_context.json  │
                        └─────────┬───────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │   Execute Step      │
                        │                     │
                        │ modify allowed      │
                        │ files only          │
                        └─────────┬───────────┘
                                  │
                                  ▼
                        update runtime.json
                                  │
                                  ▼
                              verify.sh
                                  │
                                  ▼
                              next loop


══════════════════════════════════════════════════════════════════════
                             KERNEL LAYER
══════════════════════════════════════════════════════════════════════


                     ┌───────────────────────────────┐
                     │           Odin Kernel         │
                     │                               │
                     │  kernel/*.odin                │
                     │                               │
                     │  arch/                        │
                     │  mm/                          │
                     │  sched/                       │
                     │  syscall/                     │
                     │  cap/                         │
                     │  ipc/                         │
                     │  diag/                        │
                     │                               │
                     │  built and verified by        │
                     │  odin check                   │
                     └───────────────────────────────┘


══════════════════════════════════════════════════════════════════════
                           ABI BINDINGS
══════════════════════════════════════════════════════════════════════


        contracts/kozo_abi.h
                 │
                 ▼
        tools/gen_abi.py
            │        │
            ▼        ▼

bindings/odin/abi_generated.odin
bindings/rust/src/abi.rs


ABI validator ensures layout and width consistency.
```

---

# Key Design Properties

The diagram highlights the core KOZO guarantees:

### Closed-world protocol

All identifiers originate in:

```
registry.py
invariants.py
```

---

### Deterministic execution

All harness components are pure:

```
validators
aggregator
summarizer
```

---

### Artifact-driven system

Everything flows through:

```
todo.json
runtime.json
latest_verify.json
agent_context.json
```

---

### Strict schema enforcement

All artifacts are validated against strict schemas:

```
additionalProperties: false
```

---

### Capability isolation

Security boundaries exist at two layers:

```
kernel → capability enforcement
harness → file scope enforcement
```

