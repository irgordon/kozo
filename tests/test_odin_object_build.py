import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_odin_object.sh"


class OdinObjectBuildTests(unittest.TestCase):
    def test_normalizes_obj_suffix_and_requests_single_module(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            arguments_path = root / "arguments.txt"
            self.write_fake_odin(fake_bin / "odin", arguments_path, use_obj_suffix=True)

            output_path = root / "kernel.o"
            result = self.run_builder(fake_bin, output_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            arguments = arguments_path.read_text()
            self.assertIn("-use-single-module", arguments)
            self.assertIn("-build-mode:obj", arguments)
            self.assertIn(f"-out:{output_path}", arguments)

    def test_preserves_native_output_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            arguments_path = root / "arguments.txt"
            self.write_fake_odin(fake_bin / "odin", arguments_path, use_obj_suffix=False)

            output_path = root / "kernel.o"
            result = self.run_builder(fake_bin, output_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")

    def run_builder(self, fake_bin: Path, output_path: Path):
        environment = dict(os.environ)
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        return subprocess.run(
            [str(BUILD_SCRIPT), str(output_path), "kernel", "-target:freestanding_amd64_sysv"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=environment,
        )

    def write_fake_odin(self, path: Path, arguments_path: Path, *, use_obj_suffix: bool):
        suffix_logic = 'output="${output%.o}.obj"' if use_obj_suffix else ":"
        path.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s\\n' \"$@\" > {arguments_path}\n"
            "output=''\n"
            "for argument in \"$@\"; do\n"
            "  [[ \"$argument\" == -out:* ]] && output=\"${argument#-out:}\"\n"
            "done\n"
            f"{suffix_logic}\n"
            "printf 'object\\n' > \"$output\"\n"
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
