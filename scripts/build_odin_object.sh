#!/usr/bin/env bash
set -euo pipefail

main() {
  [[ "$#" -ge 2 ]] || fail "Usage: build_odin_object.sh <output> <package> [Odin arguments]"

  local outputPath=$1
  local packagePath=$2
  shift 2

  build_single_module_object "$outputPath" "$packagePath" "$@"
  normalize_object_output "$outputPath"
}

build_single_module_object() {
  local outputPath=$1
  local packagePath=$2
  shift 2

  odin build "$packagePath" "$@" \
    -use-single-module \
    -build-mode:obj \
    "-out:$outputPath"
}

normalize_object_output() {
  local outputPath=$1
  [[ -f "$outputPath" ]] && return

  local alternatePath="${outputPath}.obj"
  if [[ "$outputPath" == *.o ]]; then
    alternatePath="${outputPath%.o}.obj"
  fi

  [[ -f "$alternatePath" ]] || fail "Odin did not emit the requested object: $outputPath"
  mv "$alternatePath" "$outputPath"
}

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

main "$@"
