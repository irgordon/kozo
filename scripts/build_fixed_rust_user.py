#!/usr/bin/env python3
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from harness.fixed_rust_user import build_user_object


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument('--fault-fixture', action='store_true')
    parser.add_argument('--response-fault-fixture', action='store_true')
    parser.add_argument('--control', type=int, default=0)
    options = parser.parse_args()
    print(json.dumps(build_user_object(ROOT, options.output,
        options.fault_fixture or options.response_fault_fixture,
        options.response_fault_fixture, options.control), indent=2))


if __name__ == '__main__':
    main()
