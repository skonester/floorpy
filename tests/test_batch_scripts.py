"""Windows regression checks: python -B -m unittest discover -s tests -v.

Build operations are stubbed; path checks call only the cleanup validator.
The cleanup lifecycle check removes only a verified disposable test fixture.
No test downloads or launches a browser.
"""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
CMD = os.environ.get("COMSPEC", "cmd.exe")


@unittest.skipUnless(os.name == "nt", "Requires Windows batch commands")
class BatchScriptTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = Path(tempfile.mkdtemp(prefix="floorpy-regression-")).resolve()
        self.temp_parent = Path(tempfile.gettempdir()).resolve()
        self.addCleanup(self.remove_sandbox)

    def remove_sandbox(self):
        # Check the resolved deletion target before removing test fixtures.
        self.assertEqual(self.sandbox.parent, self.temp_parent)
        self.assertTrue(self.sandbox.name.startswith("floorpy-regression-"))
        shutil.rmtree(self.sandbox)

    def run_batch(self, script, source, arguments=(), **environment):
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_bytes(source.replace("\n", "\r\n").encode("ascii"))
        env = os.environ.copy()
        env.update(environment)
        result = subprocess.run(
            [CMD, "/d", "/c", ".\\" + script.name, *arguments],
            cwd=script.parent,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.stderr, "", result.stdout + result.stderr)
        return result

    def check_menu(self, option, expected, failing_step="", failure_code=1,
                   arguments=(), expected_exit=None):
        source = (REPO / "Build.bat").read_text()
        menu = source.split("\n:downloadfloorp\n", 1)[0]
        choice = next(line for line in menu.splitlines() if line.startswith("choice "))
        menu = menu.replace(choice, "call :testchoice", 1)
        endings = ":success\n" + source.split("\n:success\n", 1)[1]
        if not arguments:
            endings = endings.replace(
                "if not defined NONINTERACTIVE pause", "rem Pause omitted in interactive tests."
            )
        stubs = (
            "\n:testchoice\n"
            "if defined FLOORPY_TEST_SELECTED exit /b 7\n"
            "set FLOORPY_TEST_SELECTED=1\n"
            "exit /b %FLOORPY_TEST_OPTION%\n"
        )
        for step in ("downloadfloorp", "pack", "makesfx", "resourcehack"):
            stubs += (
                f"\n:{step}\n"
                f"echo STEP {step}\n"
                f'if "%FLOORPY_TEST_FAILURE%"=="{step}" '
                "exit /b %FLOORPY_TEST_FAILURE_CODE%\n"
                "exit /b 0\n"
            )
        result = self.run_batch(
            self.sandbox / "menu-check.bat",
            menu + "\n" + endings + stubs,
            arguments=arguments,
            FLOORPY_TEST_OPTION=str(option),
            FLOORPY_TEST_FAILURE=failing_step,
            FLOORPY_TEST_FAILURE_CODE=str(failure_code),
            FLOORPY_TEST_SELECTED="",
        )
        calls = [line[5:] for line in result.stdout.splitlines() if line.startswith("STEP ")]
        self.assertEqual(calls, expected, result.stdout + result.stderr)
        if expected_exit is None:
            expected_exit = 1 if failing_step else 0
        self.assertEqual(result.returncode, expected_exit, result.stdout + result.stderr)
        if failing_step:
            self.assertIn("Build failed.", result.stdout)
        if arguments:
            self.assertNotIn("Floorpy build", result.stdout)
            self.assertNotIn("Press any key", result.stdout)

    def test_individual_menu_options(self):
        for option, step in enumerate(("downloadfloorp", "pack", "makesfx", "resourcehack"), 1):
            with self.subTest(option=option):
                self.check_menu(option, [step])

    def test_failed_menu_steps_never_run_another_operation(self):
        for option, step in enumerate(("downloadfloorp", "pack", "makesfx", "resourcehack"), 1):
            for failure_code in (1, 2):
                with self.subTest(option=option, failure_code=failure_code):
                    self.check_menu(option, [step], step, failure_code)

    def test_full_build_options(self):
        self.check_menu(5, ["pack", "makesfx", "resourcehack"])
        self.check_menu(6, ["downloadfloorp", "pack", "makesfx", "resourcehack"])

    def test_full_build_stops_at_failed_step(self):
        for option, steps in (
            (5, ["pack", "makesfx", "resourcehack"]),
            (6, ["downloadfloorp", "pack", "makesfx", "resourcehack"]),
        ):
            for index, step in enumerate(steps):
                with self.subTest(option=option, step=step):
                    self.check_menu(option, steps[: index + 1], step)

    def test_quit_runs_no_operations(self):
        self.check_menu(7, [])

    def test_unattended_builds(self):
        self.check_menu(7, ["pack", "makesfx", "resourcehack"], arguments=("--local",))
        self.check_menu(
            7, ["downloadfloorp", "pack", "makesfx", "resourcehack"], arguments=("--update",)
        )

    def test_unattended_builds_stop_on_failure(self):
        for argument, steps in (
            ("--local", ["pack", "makesfx", "resourcehack"]),
            ("--update", ["downloadfloorp", "pack", "makesfx", "resourcehack"]),
        ):
            for index, step in enumerate(steps):
                with self.subTest(argument=argument, step=step):
                    self.check_menu(7, steps[: index + 1], step, arguments=(argument,))

    def test_unsupported_build_arguments(self):
        for arguments in (("--unknown",), ("--update", "--local")):
            with self.subTest(arguments=arguments):
                self.check_menu(7, [], arguments=arguments, expected_exit=2)

    def check_cleanup(self, directory, temp_value, allowed):
        source = (REPO / "run.bat").read_text()
        validator = ":validatecleanup\n" + source.split("\n:validatecleanup\n", 1)[1]
        harness = (
            "@echo off\n"
            "setlocal EnableExtensions DisableDelayedExpansion\n"
            "call :validatecleanup\n"
            "exit /b %errorlevel%\n\n"
        )
        result = self.run_batch(directory / "guard-check.bat", harness + validator, TEMP=str(temp_value))
        self.assertEqual(result.returncode, 0 if allowed else 1, result.stdout + result.stderr)
        self.assertTrue((directory / "guard-check.bat").is_file())

    def test_cleanup_accepts_normalized_descendants(self):
        temp_dir = self.sandbox / "Temp"
        directory = temp_dir / "nested" / "Floorpy"
        for temp_value in (str(temp_dir), str(temp_dir) + "\\", str(temp_dir / "nested" / ".."), str(temp_dir).upper()):
            with self.subTest(temp_value=temp_value):
                self.check_cleanup(directory, temp_value, allowed=True)

    def test_cleanup_rejects_temp_itself_and_paths_outside_it(self):
        temp_dir = self.sandbox / "Temp"
        temp_dir.mkdir()
        for directory in (temp_dir, self.sandbox / "Temp-backups" / "Floorpy", self.sandbox / "Outside", self.sandbox):
            with self.subTest(directory=directory):
                self.check_cleanup(directory, temp_dir, allowed=False)

    def test_cleanup_rejects_missing_or_empty_temp(self):
        directory = self.sandbox / "Floorpy"
        for temp_value in ("", self.sandbox / "Missing"):
            with self.subTest(temp_value=temp_value):
                self.check_cleanup(directory, temp_value, allowed=False)

    def test_cleanup_handles_shell_metacharacters(self):
        temp_dir = self.sandbox / "Temp ! & (parentheses) ^ %PATH%"
        self.check_cleanup(temp_dir / "Floorpy ! & (nested) ^ %PATH%", temp_dir, allowed=True)
        self.check_cleanup(Path(str(temp_dir) + "-backups") / "Floorpy", temp_dir, allowed=False)

    def test_cleanup_completes_after_removing_its_own_script(self):
        temp_dir = self.sandbox / "Temp"
        directory = temp_dir / "Floorpy"
        directory.mkdir(parents=True)
        # Verify the exact recursive deletion target is inside this test's fixture.
        self.assertEqual(directory.resolve().parent, temp_dir.resolve())
        self.assertEqual(temp_dir.resolve().parent, self.sandbox)
        keep = temp_dir / "keep.txt"
        keep.write_text("Preserve sibling files.")
        source = (REPO / "run.bat").read_text()
        cleanup = "call :validatecleanup\n" + source.split("call :validatecleanup\n", 1)[1]
        cleanup = "\n".join(
            line for line in cleanup.splitlines() if not line.strip().startswith(("ping ", "pause"))
        ) + "\n"
        result = self.run_batch(
            directory / "cleanup-check.bat",
            "@echo off\nsetlocal EnableExtensions DisableDelayedExpansion\n" + cleanup,
            TEMP=str(temp_dir),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Done.", result.stdout)
        self.assertFalse(directory.exists())
        self.assertEqual(keep.read_text(), "Preserve sibling files.")

    def test_cleanup_rejects_junctions(self):
        temp_dir = self.sandbox / "Temp"
        temp_dir.mkdir()
        outside = self.sandbox / "Outside"
        outside.mkdir()
        junction = temp_dir / "redirect"
        result = subprocess.run(
            [CMD, "/d", "/c", "mklink", "/J", str(junction), str(outside)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        try:
            self.check_cleanup(junction, temp_dir, allowed=False)
            self.check_cleanup(junction / "Floorpy", temp_dir, allowed=False)
            self.check_cleanup(junction / "Floorpy", junction, allowed=False)
        finally:
            # Remove the link itself, leaving the target for normal fixture cleanup.
            junction.rmdir()


if __name__ == "__main__":
    unittest.main()
