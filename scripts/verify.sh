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
need_cmd odin
need_cmd cargo
need_cmd nm
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

filter_generated_changes() {
  local status=0
  grep -vE '(^|/)__pycache__/|\.pyc$' || status=$?
  if [[ "$status" -eq 1 ]]; then
    return 0
  fi
  return "$status"
}

collect_changed_files() {
  local head_ref
  head_ref="$(git_head_ref)"
  {
    git -C "$ROOT" diff --name-only -- . || true
    git -C "$ROOT" diff --name-only --cached "$head_ref" -- . || true
    git -C "$ROOT" ls-files --others --exclude-standard || true
  } | sed '/^$/d' | filter_generated_changes | sort -u
}

collect_evidence_files() {
  if [[ -d "$LOG_DIR" ]]; then
    find "$LOG_DIR" -type f | sort | sed "s#^$ROOT/##"
  fi
}

run_logged_command() {
  local log_file=$1
  shift

  if ! "$@" >"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: $*"
  fi
}

build_kernel_object_artifact() {
  local log_file="$LOG_DIR/nm-kernel.log"
  local object_files=()

  if ! odin build "$ROOT/kernel" -build-mode:obj "-out:$ARTIFACTS_DIR/kernel.o" >"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: odin build $ROOT/kernel -build-mode:obj -out:$ARTIFACTS_DIR/kernel.o"
  fi

  shopt -s nullglob
  object_files=("$ARTIFACTS_DIR"/kernel*.o)
  shopt -u nullglob

  if [[ "${#object_files[@]}" -eq 0 ]]; then
    cat "$log_file" >&2
    fail "Object build did not emit any kernel*.o files under $ARTIFACTS_DIR"
  fi

  if ! nm -g "${object_files[@]}" >>"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: nm -g ${object_files[*]}"
  fi
}

CHANGED_FILES_TEXT="$(collect_changed_files)"

run_logged_command "$LOG_DIR/odin-check.log" odin check "$ROOT/kernel"
run_logged_command "$LOG_DIR/odin-build.log" odin build "$ROOT/kernel"
run_logged_command "$LOG_DIR/cargo-check.log" cargo check --manifest-path "$ROOT/userspace/core_service/Cargo.toml" --target x86_64-unknown-none
build_kernel_object_artifact

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
printf "%s\n" "$VERIFY_OUTPUT"

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
