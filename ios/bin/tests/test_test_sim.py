import contextlib
from importlib.machinery import SourceFileLoader
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, call, patch


BIN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BIN_DIR))

loader = SourceFileLoader("test_sim", str(BIN_DIR / "test-sim"))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
test_sim = importlib.util.module_from_spec(spec)
loader.exec_module(test_sim)


class FakeProcess:
    def __init__(self, lines: list[str], returncode: int = 0) -> None:
        self.stdout = iter(lines)
        self.returncode = returncode
        self.killed = False

    def wait(self) -> int:
        return self.returncode

    def kill(self) -> None:
        self.killed = True


class RunXcodebuildTests(unittest.TestCase):
    def run_command(
        self,
        lines: list[str],
        selectors: list[str],
        *,
        returncode: int = 0,
    ) -> tuple[int, str, str]:
        process = FakeProcess(lines, returncode)
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(test_sim.subprocess, "Popen", return_value=process) as popen,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            result = test_sim._run_xcodebuild(["xcodebuild", "test"], selectors)

        popen.assert_called_once_with(
            ["xcodebuild", "test"],
            stdout=test_sim.subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        return result, stdout.getvalue(), stderr.getvalue()

    def test_valid_swift_testing_run_succeeds_and_streams_output(self) -> None:
        lines = [
            "Build complete\n",
            "✔ Test run with 7 tests passed after 0.100 seconds.\n",
        ]

        result, stdout, stderr = self.run_command(
            lines,
            ["LaughTrackTests/HomePodcastEpisodeDiscoveryTests"],
        )

        self.assertEqual(result, 0)
        self.assertEqual(stdout, "".join(lines))
        self.assertEqual(stderr, "")

    def test_zero_swift_testing_summary_fails_with_actionable_diagnostic(self) -> None:
        result, _, stderr = self.run_command(
            ["✔ Test run with 0 tests passed after 0.001 seconds.\n"],
            ["LaughTrackTests/MissingSuite"],
        )

        self.assertEqual(result, 1)
        self.assertIn("no Swift Testing cases ran", stderr)
        self.assertIn("LaughTrackTests/MissingSuite", stderr)
        self.assertIn("suite-level", stderr)
        self.assertIn("check-pbxproj", stderr)

    def test_missing_swift_testing_summary_fails_for_unit_test_selector(self) -> None:
        result, _, stderr = self.run_command(
            ["Executed 0 tests, with 0 failures\n", "** TEST SUCCEEDED **\n"],
            ["LaughTrackTests/UnregisteredSuite"],
        )

        self.assertEqual(result, 1)
        self.assertIn("LaughTrackTests/UnregisteredSuite", stderr)

    def test_xcodebuild_failure_is_preserved(self) -> None:
        result, _, stderr = self.run_command(
            ["✔ Test run with 0 tests passed after 0.001 seconds.\n"],
            ["LaughTrackTests/MissingSuite"],
            returncode=65,
        )

        self.assertEqual(result, 65)
        self.assertEqual(stderr, "")

    def test_xctest_selector_does_not_require_swift_testing_summary(self) -> None:
        result, _, stderr = self.run_command(
            ["Executed 1 test, with 0 failures\n"],
            ["LaughTrackUITests/AppShellTest/testLaunch"],
        )

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")


class RunSelectedTestsTests(unittest.TestCase):
    base_command = ["xcodebuild", "test"]

    def run_selected(
        self,
        processes: list[FakeProcess],
        selectors: list[str],
    ) -> tuple[int, str, str, MagicMock]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.object(test_sim.subprocess, "Popen", side_effect=processes) as popen,
            contextlib.redirect_stdout(stdout),
            contextlib.redirect_stderr(stderr),
        ):
            result = test_sim._run_selected_tests(self.base_command, selectors)

        return result, stdout.getvalue(), stderr.getvalue(), popen

    def test_mixed_valid_and_unmatched_swift_selectors_identifies_the_unmatched_selector(self) -> None:
        selectors = [
            "LaughTrackTests/ValidSuite",
            "LaughTrackTests/MissingSuite",
        ]
        valid_output = "✔ Test run with 4 tests passed after 0.100 seconds.\n"
        missing_output = "✔ Test run with 0 tests passed after 0.001 seconds.\n"

        result, stdout, stderr, popen = self.run_selected(
            [FakeProcess([valid_output]), FakeProcess([missing_output])],
            selectors,
        )

        self.assertEqual(result, 1)
        self.assertEqual(stdout, valid_output + missing_output)
        self.assertIn("LaughTrackTests/MissingSuite", stderr)
        self.assertNotIn("LaughTrackTests/ValidSuite", stderr)
        self.assertEqual(
            popen.call_args_list,
            [
                call(
                    ["xcodebuild", "test", "-only-testing:LaughTrackTests/ValidSuite"],
                    stdout=test_sim.subprocess.PIPE,
                    text=True,
                    bufsize=1,
                ),
                call(
                    ["xcodebuild", "test", "-only-testing:LaughTrackTests/MissingSuite"],
                    stdout=test_sim.subprocess.PIPE,
                    text=True,
                    bufsize=1,
                ),
            ],
        )

    def test_multiple_valid_swift_selectors_succeed_and_stream_each_run(self) -> None:
        selectors = [
            "LaughTrackTests/FirstSuite",
            "LaughTrackTests/SecondSuite",
        ]
        first_output = "first suite output\n✔ Test run with 2 tests passed after 0.100 seconds.\n"
        second_output = "second suite output\n✔ Test run with 3 tests passed after 0.100 seconds.\n"

        result, stdout, stderr, popen = self.run_selected(
            [FakeProcess([first_output]), FakeProcess([second_output])],
            selectors,
        )

        self.assertEqual(result, 0)
        self.assertEqual(stdout, first_output + second_output)
        self.assertEqual(stderr, "")
        self.assertEqual(
            popen.call_args_list,
            [
                call(
                    ["xcodebuild", "test", "-only-testing:LaughTrackTests/FirstSuite"],
                    stdout=test_sim.subprocess.PIPE,
                    text=True,
                    bufsize=1,
                ),
                call(
                    ["xcodebuild", "test", "-only-testing:LaughTrackTests/SecondSuite"],
                    stdout=test_sim.subprocess.PIPE,
                    text=True,
                    bufsize=1,
                ),
            ],
        )

    def test_upstream_failure_is_preserved_and_stops_later_selectors(self) -> None:
        selectors = [
            "LaughTrackTests/FirstSuite",
            "LaughTrackTests/FailingSuite",
            "LaughTrackTests/NeverRunsSuite",
        ]

        result, _, stderr, popen = self.run_selected(
            [
                FakeProcess(["✔ Test run with 2 tests passed after 0.100 seconds.\n"]),
                FakeProcess(["xcodebuild failed\n"], returncode=65),
            ],
            selectors,
        )

        self.assertEqual(result, 65)
        self.assertEqual(stderr, "")
        self.assertEqual(popen.call_count, 2)

    def test_xctest_selectors_remain_grouped_and_do_not_require_a_swift_summary(self) -> None:
        selectors = [
            "LaughTrackTests/FirstSuite",
            "LaughTrackTests/SecondSuite",
            "LaughTrackUITests/AppShellTest/testLaunch",
            "LaughTrackUITests/AppShellTest/testNavigation",
        ]

        result, _, stderr, popen = self.run_selected(
            [
                FakeProcess(["✔ Test run with 2 tests passed after 0.100 seconds.\n"]),
                FakeProcess(["✔ Test run with 3 tests passed after 0.100 seconds.\n"]),
                FakeProcess(["Executed 2 tests, with 0 failures\n"]),
            ],
            selectors,
        )

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            popen.call_args_list[-1],
            call(
                [
                    "xcodebuild",
                    "test",
                    "-only-testing:LaughTrackUITests/AppShellTest/testLaunch",
                    "-only-testing:LaughTrackUITests/AppShellTest/testNavigation",
                ],
                stdout=test_sim.subprocess.PIPE,
                text=True,
                bufsize=1,
            ),
        )


if __name__ == "__main__":
    unittest.main()
