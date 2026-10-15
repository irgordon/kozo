#!/usr/bin/env python3
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.fixed_rust_user import build_user_object


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: build_fixed_rust_user.py <fixed_user.o>')
    print(json.dumps(build_user_object(ROOT, Path(sys.argv[1])), indent=2))


if __name__ == '__main__':
    main()
