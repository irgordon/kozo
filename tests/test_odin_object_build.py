import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_odin_object.sh"
BASH = shutil.which("bash")


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

    def test_normalizes_dot_obj_output_for_suffixless_request(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "dot_obj")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            self.assertFalse(Path(f"{output_path}.obj").exists())

    def test_rejects_unsupported_double_dot_o_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel.o"
            result, _ = self.run_builder(root, output_path, "dot_o")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("emitted no supported object", result.stderr)

    def test_rejects_exact_and_dot_obj_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "exact_and_obj")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple supported objects", result.stderr)

    def test_rejects_dot_o_and_dot_obj_output(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "o_and_obj")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("multiple supported objects", result.stderr)

    def test_stale_dot_obj_output_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            alternate_path = Path(f"{output_path}.obj")
            alternate_path.write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(alternate_path.exists())

    def test_stale_legacy_dot_obj_output_cannot_pass(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel.o"
            alternate_path = root / "kernel.obj"
            alternate_path.write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(alternate_path.exists())

    def test_removes_all_stale_candidates_before_exact_build(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            output_path.write_text("stale\n")
            Path(f"{output_path}.o").write_text("stale\n")
            Path(f"{output_path}.obj").write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "exact")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")
            self.assertFalse(Path(f"{output_path}.o").exists())
            self.assertFalse(Path(f"{output_path}.obj").exists())

    def test_rejects_stale_exact_directory(self):
        self.assert_stale_directory_rejected("")

    def test_rejects_stale_dot_o_directory(self):
        self.assert_stale_directory_rejected(".o")

    def test_rejects_stale_dot_obj_directory(self):
        self.assert_stale_directory_rejected(".obj")

    def test_rejects_emitted_dot_o_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "dot_o_directory")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a regular file", result.stderr)

    def test_rejects_emitted_dot_obj_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, _ = self.run_builder(root, output_path, "dot_obj_directory")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a regular file", result.stderr)

    def test_preserves_nested_output_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "nested" / "objects" / "kernel-build-check"
            output_path.parent.mkdir(parents=True)
            result, _ = self.run_builder(root, output_path, "dot_o")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output_path.read_text(), "object\n")

    def test_preserves_package_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            package_path = root / "package with spaces"
            result, arguments_path = self.run_builder(
                root, output_path, "exact", package_path=package_path
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(str(package_path), arguments_path.read_text().splitlines())

    def test_preserves_additional_argument_with_spaces(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            argument = "-define:MESSAGE=two words"
            result, arguments_path = self.run_builder(
                root, output_path, "exact", additional_arguments=[argument]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(argument, arguments_path.read_text().splitlines())

    def test_preserves_additional_argument_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            arguments = ["-target:first", "-define:SECOND=2"]
            result, arguments_path = self.run_builder(
                root, output_path, "exact", additional_arguments=arguments
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            lines = arguments_path.read_text().splitlines()
            self.assertLess(lines.index(arguments[0]), lines.index(arguments[1]))

    def test_requests_build_before_package(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, arguments_path = self.run_builder(root, output_path, "exact")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(arguments_path.read_text().splitlines()[:2], ["build", "kernel"])

    def test_requests_build_mode_once(self):
        self.assert_argument_count("-build-mode:obj", 1)

    def test_requests_single_module_once(self):
        self.assert_argument_count("-use-single-module", 1)

    def test_passes_target_argument_once(self):
        self.assert_argument_count("-target:freestanding_amd64_sysv", 1)

    def test_compiler_failure_removes_stale_candidates_first(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            candidates = [output_path, Path(f"{output_path}.o"), Path(f"{output_path}.obj")]
            for candidate in candidates:
                candidate.write_text("stale\n")
            result, _ = self.run_builder(root, output_path, "failure")

            self.assertEqual(result.returncode, 23)
            self.assertFalse(any(candidate.exists() for candidate in candidates))

    def test_rejects_missing_all_arguments(self):
        result = self.run_raw_builder([])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)

    def test_rejects_missing_package_argument(self):
        result = self.run_raw_builder(["kernel.o"])

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)

    def test_reports_exact_dot_o_and_dot_obj_forms(self):
        cases = (("exact", "exact"), ("dot_o", "dot_o"), ("dot_obj", "dot_obj"))
        for mode, expected_form in cases:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                output_path = root / "kernel-build-check"
                result, _ = self.run_builder(root, output_path, mode)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(
                    f"KOZO_ODIN_OBJECT_OUTPUT_FORM={expected_form}", result.stdout
                )

    def assert_stale_directory_rejected(self, suffix: str):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            Path(f"{output_path}{suffix}").mkdir()
            result, _ = self.run_builder(root, output_path, "none")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not a regular file", result.stderr)

    def assert_argument_count(self, expected: str, count: int):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_path = root / "kernel-build-check"
            result, arguments_path = self.run_builder(root, output_path, "exact")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(arguments_path.read_text().splitlines().count(expected), count)

    def run_raw_builder(self, arguments: list[str]):
        self.assertIsNotNone(BASH, "The governed host contract requires Bash")
        return subprocess.run(
            [BASH, str(BUILD_SCRIPT), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

    def run_builder(
        self,
        root: Path,
        output_path: Path,
        mode: str,
        package_path: Path | str = "kernel",
        additional_arguments: list[str] | None = None,
    ):
        fake_bin = root / "bin"
        fake_bin.mkdir()
        arguments_path = root / "arguments.txt"
        self.write_fake_odin(fake_bin / "odin")

        environment = dict(os.environ)
        environment["PATH"] = os.pathsep.join((str(fake_bin), environment["PATH"]))
        environment["FAKE_ODIN_ARGUMENTS"] = str(arguments_path)
        environment["FAKE_ODIN_MODE"] = mode
        arguments = additional_arguments or ["-target:freestanding_amd64_sysv"]
        self.assertIsNotNone(BASH, "The governed host contract requires Bash")
        result = subprocess.run(
            [BASH, str(BUILD_SCRIPT), str(output_path), str(package_path), *arguments],
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
            "  exact_and_obj)\n"
            "    printf 'object\\n' > \"$output\"\n"
            "    printf 'object\\n' > \"${output}.obj\"\n"
            "    ;;\n"
            "  o_and_obj)\n"
            "    printf 'object\\n' > \"${output}.o\"\n"
            "    printf 'object\\n' > \"${output}.obj\"\n"
            "    ;;\n"
            "  none) : ;;\n"
            "  failure) exit 23 ;;\n"
            "  directory) mkdir \"$output\" ;;\n"
            "  dot_o_directory) mkdir \"${output}.o\" ;;\n"
            "  dot_obj_directory) mkdir \"${output}.obj\" ;;\n"
            "  *) exit 24 ;;\n"
            "esac\n"
        )
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
