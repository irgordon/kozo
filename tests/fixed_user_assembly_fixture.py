"""Historical user payload and ELF records from accepted pre-Rust 4fdea571."""
from pathlib import Path
import json


def historical_elf_report(report):
    fixture = Path(__file__).parent / 'fixtures/fixed_user_assembly.v0.elf.json'
    return report | json.loads(fixture.read_text())


def historical_user_assembly(source):
    fixture = Path(__file__).parent / 'fixtures/fixed_user_assembly.v0.asm'
    start = source.index('user_probe_code_start:')
    end = source.index('section .bss', start)
    return source[:start] + fixture.read_text() + '\n' + source[end:]
