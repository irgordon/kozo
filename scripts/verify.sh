#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKS_DIR="$ROOT/tasks"
ARTIFACTS_DIR="$ROOT/artifacts"
LOG_DIR="$ARTIFACTS_DIR/logs"

TODO_JSON="$TASKS_DIR/todo.json"
RUNTIME_JSON="$TASKS_DIR/runtime.json"
VERIFY_JSON="$ARTIFACTS_DIR/latest_verify.json"
LESSONS_JSON="$TASKS_DIR/lessons.json"

mkdir -p "$LOG_DIR"

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

need_file() {
  [[ -f "$1" ]] || fail "Required file missing: $1"
}

need_cmd python3
need_cmd git
need_file "$TODO_JSON"
need_file "$RUNTIME_JSON"
need_file "$LESSONS_JSON"

RUN_ID="verify-$(date -u +"%Y%m%dT%H%M%SZ")"
GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

CHANGED_FILES_TEXT="$(
  {
    git -C "$ROOT" diff --name-only HEAD -- . || true
    git -C "$ROOT" diff --name-only --cached -- . || true
    git -C "$ROOT" ls-files --others --exclude-standard || true
  } | sed '/^$/d' | grep -vE '(^|/)__pycache__/|\.pyc$' | sort -u
)"

EVIDENCE_FILES_TEXT="$(
  if [[ -d "$LOG_DIR" ]]; then
    find "$LOG_DIR" -type f | sort | sed "s#^$ROOT/##"
  fi
)"

VERIFY_OUTPUT="$(
ROOT="$ROOT" \
CHANGED_FILES_TEXT="$CHANGED_FILES_TEXT" \
EVIDENCE_FILES_TEXT="$EVIDENCE_FILES_TEXT" \
RUN_ID="$RUN_ID" \
GENERATED_AT="$GENERATED_AT" \
python3 - <<'PY'
import json
import os
from pathlib import Path

from harness.aggregator import run_aggregator

root = Path(os.environ["ROOT"])
changed_files = [line for line in os.environ.get("CHANGED_FILES_TEXT", "").splitlines() if line]
evidence_files = [line for line in os.environ.get("EVIDENCE_FILES_TEXT", "").splitlines() if line]
run_id = os.environ["RUN_ID"]
generated_at = os.environ["GENERATED_AT"]

todo = json.loads((root / "tasks" / "todo.json").read_text())
runtime = json.loads((root / "tasks" / "runtime.json").read_text())
json.loads((root / "tasks" / "lessons.json").read_text())

bundle = {
    "todo": todo,
    "runtime": runtime,
    "root_dir": str(root),
}

artifact = run_aggregator(
    artifact_bundle=bundle,
    changed_files=changed_files,
    evidence_files=evidence_files,
    run_id=run_id,
    generated_at=generated_at,
)

print(json.dumps(artifact, indent=2))
PY
)"

printf "%s\n" "$VERIFY_OUTPUT" > "$VERIFY_JSON"

STATUS="$(
python3 - "$VERIFY_JSON" <<'PY'
import json, sys
print(json.loads(open(sys.argv[1]).read())["status"])
PY
)"

if [[ "$STATUS" == "fail" ]]; then
  echo "VERIFY: FAIL"
  exit 1
fi

echo "VERIFY: PASS"
exit 0
