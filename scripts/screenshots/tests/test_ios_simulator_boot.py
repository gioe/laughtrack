import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
FASTFILE = REPO_ROOT / "ios" / "fastlane" / "Fastfile"

BOOT_HARNESS = r"""
require "json"

$lanes = {}
$events = []

def default_platform(*)
end

def platform(*)
  yield
end

def before_all(*)
end

def desc(*)
end

def lane(name, &block)
  $lanes[name] = block
end

module UI
  def self.message(message)
    $events << ["message", message]
  end

  def self.success(*)
  end

  def self.user_error!(message)
    raise RuntimeError, message
  end
end

load ARGV.fetch(0)

$boot_results = case ARGV.fetch(1)
when "success", "ui_failure"
  [:success]
when "recover"
  [:timeout, :success]
when "fail"
  [:timeout, :timeout]
else
  raise "unknown scenario"
end

def wait_for_screenshot_simulator_boot(udid, timeout_seconds: SCREENSHOT_SIMULATOR_BOOT_TIMEOUT_SECONDS)
  $events << ["bootstatus", udid, timeout_seconds]
  result = $boot_results.shift
  if result == :timeout
    raise ScreenshotSimulatorBootTimeout,
          "simctl bootstatus for #{udid} exceeded #{timeout_seconds} seconds"
  end
end

def system(*arguments, **)
  $events << arguments
  true
end

native_target = {
  version: "18.3.1",
  devices: {"iPhone 16 Pro Max" => "test-simulator-udid"},
}

error = nil
begin
  boot_screenshot_simulator(native_target, "iPhone 16 Pro Max")
  raise "synthetic screenshot UI-test failure" if ARGV.fetch(1) == "ui_failure"
rescue => caught
  error = {"class" => caught.class.name, "message" => caught.message}
end

puts JSON.generate({"events" => $events, "error" => error})
"""

TIMEOUT_HARNESS = r"""
require "json"
require "rbconfig"

$lanes = {}

def default_platform(*)
end

def platform(*)
  yield
end

def before_all(*)
end

def desc(*)
end

def lane(name, &block)
  $lanes[name] = block
end

module UI
  def self.message(*)
  end

  def self.success(*)
  end

  def self.user_error!(message)
    raise RuntimeError, message
  end
end

load ARGV.fetch(0)

started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)
error = nil
begin
  run_screenshot_command_with_timeout(
    [RbConfig.ruby, "-e", "sleep 30"],
    timeout_seconds: 0.05,
    timeout_message: "bounded boot deadline reached",
  )
rescue => caught
  error = {"class" => caught.class.name, "message" => caught.message}
end
elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at

puts JSON.generate({"elapsed" => elapsed, "error" => error})
"""


def run_harness(source: str, scenario: str | None = None) -> dict:
    command = ["ruby", "-e", source, str(FASTFILE)]
    if scenario is not None:
        command.append(scenario)
    result = subprocess.run(
        command,
        cwd=FASTFILE.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def command_events(result: dict) -> list[list[str]]:
    return [event for event in result["events"] if event[0] != "message"]


def test_boot_readiness_has_an_explicit_bounded_deadline() -> None:
    result = run_harness(BOOT_HARNESS, "success")

    assert command_events(result)[0] == ["bootstatus", "test-simulator-udid", 120]
    assert result["error"] is None


def test_first_timeout_performs_one_safe_restart_then_retries() -> None:
    result = run_harness(BOOT_HARNESS, "recover")

    assert command_events(result) == [
        ["bootstatus", "test-simulator-udid", 120],
        ["xcrun", "simctl", "shutdown", "test-simulator-udid"],
        ["xcrun", "simctl", "boot", "test-simulator-udid"],
        ["bootstatus", "test-simulator-udid", 120],
        ["xcrun", "simctl", "uninstall", "test-simulator-udid", "app.laughtrack.ios"],
    ]
    assert result["error"] is None


def test_second_timeout_is_infrastructure_failure_without_another_restart() -> None:
    result = run_harness(BOOT_HARNESS, "fail")

    assert command_events(result) == [
        ["bootstatus", "test-simulator-udid", 120],
        ["xcrun", "simctl", "shutdown", "test-simulator-udid"],
        ["xcrun", "simctl", "boot", "test-simulator-udid"],
        ["bootstatus", "test-simulator-udid", 120],
    ]
    assert result["error"]["class"] == "RuntimeError"
    assert "simulator infrastructure failure after one restart" in result["error"]["message"]


def test_ui_test_failure_propagates_without_boot_recovery() -> None:
    result = run_harness(BOOT_HARNESS, "ui_failure")

    assert command_events(result) == [
        ["bootstatus", "test-simulator-udid", 120],
        ["xcrun", "simctl", "uninstall", "test-simulator-udid", "app.laughtrack.ios"],
    ]
    assert result["error"] == {
        "class": "RuntimeError",
        "message": "synthetic screenshot UI-test failure",
    }


def test_timeout_runner_terminates_a_stalled_child_promptly() -> None:
    result = run_harness(TIMEOUT_HARNESS)

    assert result["error"] == {
        "class": "ScreenshotSimulatorBootTimeout",
        "message": "bounded boot deadline reached",
    }
    assert result["elapsed"] < 2
