#!/usr/bin/env bash
set -euo pipefail

main() {
  [[ "$#" -ge 2 ]] || fail "Usage: build_odin_object.sh <output> <package> [Odin arguments]"

  local outputPath=$1
  local packagePath=$2
  shift 2

  prepare_object_output_paths "$outputPath"
  build_single_module_object "$outputPath" "$packagePath" "$@"
  normalize_object_output "$outputPath"
  validate_canonical_object "$outputPath"
}

prepare_object_output_paths() {
  local outputPath=$1
  local candidatePath

  while IFS= read -r -d '' candidatePath; do
    remove_stale_candidate "$candidatePath"
  done < <(supported_object_paths "$outputPath")
}

remove_stale_candidate() {
  local candidatePath=$1
  candidate_exists "$candidatePath" || return 0
  is_regular_file "$candidatePath" || fail "Existing object candidate is not a regular file: $candidatePath"
  rm -f -- "$candidatePath" || fail "Failed to remove stale object candidate: $candidatePath"
}

build_single_module_object() {
  local outputPath=$1
  local packagePath=$2
  shift 2

  if odin build "$packagePath" "$@" \
      -use-single-module \
      -build-mode:obj \
      "-out:$outputPath"; then
    return
  else
    local compilerStatus=$?
    printf "FAIL: Odin invocation failed for object: %s\n" "$outputPath" >&2
    return "$compilerStatus"
  fi
}

normalize_object_output() {
  local outputPath=$1
  local candidatePath
  local emittedPaths=()

  while IFS= read -r -d '' candidatePath; do
    candidate_exists "$candidatePath" || continue
    is_regular_file "$candidatePath" || fail "Odin output is not a regular file: $candidatePath"
    emittedPaths+=("$candidatePath")
  done < <(supported_object_paths "$outputPath")

  [[ "${#emittedPaths[@]}" -gt 0 ]] || fail "Odin completed but emitted no supported object for: $outputPath"
  [[ "${#emittedPaths[@]}" -eq 1 ]] || fail "Odin emitted multiple supported objects for: $outputPath"

  [[ "${emittedPaths[0]}" == "$outputPath" ]] && return
  mv -- "${emittedPaths[0]}" "$outputPath" || fail "Failed to normalize Odin object output: $outputPath"
}

supported_object_paths() {
  local outputPath=$1
  printf '%s\0' "$outputPath"
  if [[ "$outputPath" == *.o ]]; then
    printf '%s\0' "${outputPath%.o}.obj"
  else
    printf '%s\0' "${outputPath}.o" "${outputPath}.obj"
  fi
}

validate_canonical_object() {
  local outputPath=$1
  is_regular_file "$outputPath" || fail "Canonical Odin object is not a regular file: $outputPath"
}

candidate_exists() {
  [[ -e "$1" || -L "$1" ]]
}

is_regular_file() {
  [[ -f "$1" && ! -L "$1" ]]
}

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

main "$@"
