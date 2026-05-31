#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKS_DIR="$ROOT/tasks"
ARTIFACTS_DIR="$ROOT/artifacts"
LOG_DIR="$ARTIFACTS_DIR/logs"

TODO_JSON="$TASKS_DIR/todo.json"
RUNTIME_JSON="$TASKS_DIR/runtime.json"
LESSONS_JSON="$TASKS_DIR/lessons.json"
VERIFY_JSON="$ARTIFACTS_DIR/latest_verify.json"

EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"
KERNEL_BUILD_CHECK="$ARTIFACTS_DIR/kernel-build-check"
VERIFY_TMP=""

mkdir -p "$LOG_DIR" "$ARTIFACTS_DIR"

cleanup() {
  [[ -n "${VERIFY_TMP:-}" && -f "$VERIFY_TMP" ]] && rm -f "$VERIFY_TMP"
  rm -f "$KERNEL_BUILD_CHECK"
}

trap cleanup EXIT

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

repo_head_ref() {
  if git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
    printf "HEAD"
    return
  fi

  printf "%s" "$EMPTY_TREE"
}

filter_generated_changes() {
  local status=0

  grep -vE '(^|/)__pycache__/|\.pyc$|^artifacts/latest_verify\.json$|^artifacts/logs/|^artifacts/kernel.*\.o$|^artifacts/kernel-build-check$' || status=$?

  if [[ "$status" -eq 1 ]]; then
    return 0
  fi

  return "$status"
}

collect_changed_files() {
  local head_ref
  head_ref="$(repo_head_ref)"

  {
    git -C "$ROOT" diff --name-only --diff-filter=ACMRT -- . || true
    git -C "$ROOT" diff --name-only --cached --diff-filter=ACMRT "$head_ref" -- . || true
    git -C "$ROOT" ls-files --others --exclude-standard || true
  } | sed '/^$/d' | filter_generated_changes | sort -u
}

collect_evidence_files() {
  local files=(
    "$LOG_DIR/odin-check.log"
    "$LOG_DIR/odin-build.log"
    "$LOG_DIR/cargo-check.log"
    "$LOG_DIR/nm-kernel.log"
  )

  local file
  for file in "${files[@]}"; do
    [[ -f "$file" ]] && printf "%s\n" "${file#"$ROOT/"}"
  done
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

  find "$ARTIFACTS_DIR" -maxdepth 1 -type f -name 'kernel*.o' -delete

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

validate_verify_artifact() {
  local verify_path=$1

  ROOT="$ROOT" python3 - "$verify_path" <<'PY'
import json
import sys
from pathlib import Path

from harness.validators_impl.schema import validate_named_document

verify_path = Path(sys.argv[1])
verify = json.loads(verify_path.read_text())

validate_named_document("latest_verify", verify)

print(verify["status"])
PY
}

write_verify_artifact_atomically() {
  local verify_output=$1

  VERIFY_TMP="$(mktemp "$ARTIFACTS_DIR/latest_verify.XXXXXX.tmp")"
  printf "%s\n" "$verify_output" >"$VERIFY_TMP"

  local status
  status="$(validate_verify_artifact "$VERIFY_TMP")"

  mv "$VERIFY_TMP" "$VERIFY_JSON"
  VERIFY_TMP=""

  printf "%s\n" "$status"
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

CHANGED_FILES_TEXT="$(collect_changed_files)"

run_logged_command "$LOG_DIR/odin-check.log" \
  odin check "$ROOT/kernel"

run_logged_command "$LOG_DIR/odin-build.log" \
  odin build "$ROOT/kernel" "-out:$KERNEL_BUILD_CHECK"

run_logged_command "$LOG_DIR/cargo-check.log" \
  cargo check --manifest-path "$ROOT/userspace/core_service/Cargo.toml" --target x86_64-unknown-none

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
changed_files = [
    line
    for line in os.environ.get("CHANGED_FILES_TEXT", "").splitlines()
    if line
]
evidence_files = [
    line
    for line in os.environ.get("EVIDENCE_FILES_TEXT", "").splitlines()
    if line
]

todo = json.loads((root / "tasks" / "todo.json").read_text())
runtime = json.loads((root / "tasks" / "runtime.json").read_text())
lessons = json.loads((root / "tasks" / "lessons.json").read_text())

bundle = {
    "todo": todo,
    "runtime": runtime,
    "lessons": lessons,
    "root_dir": str(root),
}

artifact = run_aggregator(
    artifact_bundle=bundle,
    changed_files=changed_files,
    evidence_files=evidence_files,
    run_id=os.environ["RUN_ID"],
    generated_at=os.environ["GENERATED_AT"],
)

print(json.dumps(artifact, indent=2))
PY
)"

STATUS="$(write_verify_artifact_atomically "$VERIFY_OUTPUT")"

printf "%s\n" "$VERIFY_OUTPUT"

if [[ "$STATUS" == "fail" ]]; then
  echo "VERIFY: FAIL"
  exit 1
fi

if [[ "$STATUS" != "pass" ]]; then
  fail "Unexpected verification status: $STATUS"
fi

echo "VERIFY: PASS"
exit 0