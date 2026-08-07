import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_odin_object.sh"


class OdinObjectBuildTests(unittest.TestCase):
    def test_accepts_exact_output_and_requests_single_module(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, arguments_path = self.run_builder(root, output_path, "exact")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            arguments = arguments_path.read_text()
            self.assertIn("-use-single-module", arguments)
            self.assertIn("-build-mode:obj", arguments)
            self.assertIn(f"-out:{output_path}", arguments)

    def test_normalizes_dot_o_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            alternate_path = Path(f"{output_path}.o")
            result, _ = self.run_builder(root, output_path, "dot_o")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            self.assertFalse(alternate_path.exists())

    def test_preserves_legacy_obj_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel.o"
            alternate_path = root / "kernel.obj"
            result, _ = self.run_builder(root, output_path, "dot_obj")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            self.assertFalse(alternate_path.exists())

    def test_preserves_compiler_failure(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "failure")

            self.assertEqual(result.returncode, 23)
            self.assertIn("Odin invocation failed", result.stderr)
            self.assertFalse(output_path.exists())

    def test_rejects_missing_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("emitted no supported object", result.stderr)

    def test_rejects_ambiguous_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "both")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple supported objects", result.stderr)

    def test_stale_exact_output_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            output_path.write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output_path.exists())

    def test_stale_dot_o_output_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            alternate_path = Path(f"{output_path}.o")
            alternate_path.write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(alternate_path.exists())

    def test_rejects_invalid_output_type(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "directory")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a regular file", result.stderr)

    def test_preserves_paths_with_spaces(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "nested output" / "kernel build check"
            output_path.parent.mkdir()
            result, _ = self.run_builder(root, output_path, "dot_o")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")

    def run_builder(self, root: Path, output_path: Path, mode: str):
        fake_bin = root / "bin"
        fake_bin.mkdir()
        arguments_path = root / "arguments.txt"
        self.write_fake_odin(fake_bin / "odin")

        environment = dict(os.environ)
        environment["PATH"] = f"{fake_bin}:{environment['PATH']}"
        environment["FAKE_ODIN_ARGUMENTS"] = str(arguments_path)
        environment["FAKE_ODIN_MODE"] = mode
        result = subprocess.run(
            [str(BUILD_SCRIPT), str(output_path), "kernel", "-target:freestanding_amd64_sysv"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=environment,
        )
        return result, arguments_path

    def write_fake_odin(self, path: Path):
        path.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '%s\\n' \"$@\" > \"$FAKE_ODIN_ARGUMENTS\"\n"
            "output=''\n"
            "for argument in \"$@\"; do\n"
            "  [[ \"$argument\" == -out:* ]] && output=\"${argument#-out:}\"\n"
            "done\n"
            "case \"$FAKE_ODIN_MODE\" in\n"
            "  exact) printf 'object\\n' > \"$output\" ;;\n"
            "  dot_o) printf 'object\\n' > \"${output}.o\" ;;\n"
            "  dot_obj) printf 'object\\n' > \"${output%.o}.obj\" ;;\n"
            "  both)\n"
            "    printf 'object\\n' > \"$output\"\n"
            "    printf 'object\\n' > \"${output}.o\"\n"
            "    ;;\n"
            "  none) : ;;\n"
            "  failure) exit 23 ;;\n"
            "  directory) mkdir \"$output\" ;;\n"
            "  *) exit 24 ;;\n"
            "esac\n"
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
