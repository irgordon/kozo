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
EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"

git_head_ref() {
  if git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
    printf "HEAD"
    return
  fi
  printf "%s" "$EMPTY_TREE"
}

collect_changed_files() {
  local head_ref
  head_ref="$(git_head_ref)"
  {
    git -C "$ROOT" diff --name-only -- . || true
    git -C "$ROOT" diff --name-only --cached "$head_ref" -- . || true
    git -C "$ROOT" ls-files --others --exclude-standard || true
  } | sed '/^$/d' | grep -vE '(^|/)__pycache__/|\.pyc$' | sort -u
}

collect_evidence_files() {
  if [[ -d "$LOG_DIR" ]]; then
    find "$LOG_DIR" -type f | sort | sed "s#^$ROOT/##"
  fi
}

CHANGED_FILES_TEXT="$(collect_changed_files)"

EVIDENCE_FILES_TEXT="$(collect_evidence_files)"

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
ROOT="$ROOT" python3 - "$VERIFY_JSON" <<'PY'
import json
import os
import sys
from pathlib import Path

from harness.validators_impl.schema import validate_named_document

verify_path = Path(sys.argv[1])
verify = json.loads(verify_path.read_text())
validate_named_document("latest_verify", verify)
print(verify["status"])
PY
)"

if [[ "$STATUS" == "fail" ]]; then
  echo "VERIFY: FAIL"
  exit 1
fi

echo "VERIFY: PASS"
exit 0
