#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TODO_JSON="$ROOT/tasks/todo.json"
RUNTIME_JSON="$ROOT/tasks/runtime.json"
VERIFY_JSON="$ROOT/artifacts/latest_verify.json"
OUTPUT_JSON="$ROOT/agent/agent_context.json"

mkdir -p "$ROOT/agent"

python3 - "$TODO_JSON" "$RUNTIME_JSON" "$VERIFY_JSON" "$OUTPUT_JSON" <<'PY'
import json
import sys
from pathlib import Path
from harness.summarize import summarize

todo = json.loads(Path(sys.argv[1]).read_text())
runtime = json.loads(Path(sys.argv[2]).read_text())
verify = json.loads(Path(sys.argv[3]).read_text())
output = Path(sys.argv[4])

context = summarize(todo, runtime, verify)
output.write_text(json.dumps(context, indent=2) + "\n")
PY

echo "PASS: agent_context.json generated"
