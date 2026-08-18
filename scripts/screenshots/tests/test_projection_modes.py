import json
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]

FASTFILE_HARNESS = r"""
require "json"

$lanes = {}
$events = []
$cold_cache = ARGV.fetch(3) == "cold"

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
    raise message
  end
end

load ARGV.fetch(0)

case ARGV.fetch(1)
when "ios"
  def ios_screenshot_native_target
    devices = IOS_SCREENSHOT_PROFILES.to_h do |profile|
      [profile.fetch(:device_name), "test-simulator-udid"]
    end
    {environment: {xcode: {}, simulator_runtime: {}}, version: "18.3.1", devices: devices}
  end

  def plan_ios_screenshot_cache(*)
    pending_profiles = $cold_cache ? ["ios_phone"] : []
    {
      "pending_profiles" => pending_profiles,
      "reused_profiles" => [],
      "profile_fingerprints" => {"ios_phone" => "cold-cache-fingerprint"},
    }
  end

  def with_screenshot_fixture_server
    yield
  end

  def boot_screenshot_simulator(*)
  end

  def patch_snapshot_destination_for_18_3_1
  end

  def patch_targeted_snapshot_one_shot
    $events << "patch_targeted_snapshot_one_shot"
  end

  def with_targeted_screenshot_completion_watchdog(scenario_ids)
    $events << {"watchdog" => scenario_ids}
    yield
  end

  def run_tests(**options)
    $events << {"run_tests" => options}
  end

  def capture_screenshots(**options)
    $events << {"capture" => options}
  end

  def store_ios_screenshot_profile(*)
  end

  def validate_ios_screenshot_collection(*)
  end

  def collect_ios_screenshot_run(*, **options)
    $events << {"collect" => options}
  end

  def export_app_store_projection(*)
    $events << "project"
  end
when "android"
  def android_screenshot_native_target
    {environment: {jdk: {}, build_tools: {}, system_image: {}}, adb: "adb", emulator: "emulator", avd: "test"}
  end

  def plan_android_screenshot_cache(*)
    {"pending_profiles" => [], "reused_profiles" => [], "profile_fingerprints" => {}}
  end

  def boot_screenshot_emulator(native_target)
    ["adb", "serial"]
  end

  def with_screenshot_fixture_server
    yield
  end

  def gradle(**)
  end

  def capture_screenshot_profile(*, **options)
    $events << {"capture" => options}
  end

  def validate_screenshot_profile!(*)
  end

  def collect_android_screenshot_run(*, **options)
    $events << {"collect" => options}
  end

  def export_play_projection(*)
    $events << "project"
  end
else
  raise "unknown platform"
end

options = {run_root: ARGV.fetch(2)}
options[:comparison_only] = true if ARGV.fetch(3) == "comparison"
if ARGV.fetch(3).start_with?("targeted")
  if ARGV.fetch(3) == "targeted_favorites"
    options[:profiles] = ARGV.fetch(1) == "ios" ? "ios_phone" : "android_phone"
    options[:scenarios] = "15_AuthenticatedFavorites"
    options[:fixture_mode] = "curated"
  else
    options[:profiles] = ARGV.fetch(1) == "ios" ? "ios_phone,ios_large_tablet" : "android_phone"
    options[:scenarios] = "02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts,10_PodcastEpisodeDetail"
  end
  $lanes.fetch(:verify_screenshots).call(options)
else
  $lanes.fetch(:screenshots).call(options)
end
puts JSON.generate($events)
"""

ONE_SHOT_LAUNCHER_HARNESS = r"""
require "json"

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

  def self.user_error!(message)
    raise RuntimeError, message
  end
end

load ARGV.fetch(0)

LauncherConfig = Struct.new(:number_of_retries)

module Snapshot
  class SimulatorLauncher
    attr_reader :launcher_config, :launches

    def initialize(number_of_retries)
      @launcher_config = LauncherConfig.new(number_of_retries)
      @launches = []
    end

    def launch_simultaneously(devices, language, locale, launch_arguments)
      @launches << [devices, language, locale, launch_arguments]
    end
  end
end

patch_targeted_snapshot_one_shot
patch_targeted_snapshot_one_shot

one_shot = Snapshot::SimulatorLauncher.new(0)
phone = ["iPhone 16 Pro Max"]
arguments = ["-UITestMockMode -ScreenshotScenarios 15_AuthenticatedFavorites"]
one_shot.launch_simultaneously(phone, "en-US", nil, arguments)
duplicate_result = one_shot.launch_simultaneously(phone.dup, "en-US", nil, arguments.dup)
one_shot.launch_simultaneously(["iPad Pro 13-inch (M4)"], "en-US", nil, arguments)
one_shot.launch_simultaneously(phone, "fr-FR", nil, arguments)

retryable = Snapshot::SimulatorLauncher.new(1)
2.times { retryable.launch_simultaneously(phone, "en-US", nil, arguments) }

puts JSON.generate(
  {
    "one_shot_launches" => one_shot.launches,
    "duplicate_result" => duplicate_result,
    "retryable_launches" => retryable.launches,
    "guard_ancestor_count" => Snapshot::SimulatorLauncher.ancestors.count do |ancestor|
      ancestor == LaughTrackTargetedSnapshotOneShot
    end,
  },
)
"""

WATCHDOG_HARNESS = r"""
require "json"
require "tmpdir"

$lanes = {}
$messages = []

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
    $messages << message
  end

  def self.user_error!(message)
    raise RuntimeError, message
  end
end

load ARGV.fetch(0)

process_table = <<~TABLE
  100 /bin/sh -c xcodebuild -derivedDataPath #{SCREENSHOT_DERIVED_DATA_PATH} test-without-building
  101 /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -derivedDataPath #{SCREENSHOT_DERIVED_DATA_PATH} test-without-building
  102 /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -derivedDataPath /tmp/other test-without-building
  103 /Applications/Xcode.app/Contents/Developer/usr/bin/xcodebuild -derivedDataPath #{SCREENSHOT_DERIVED_DATA_PATH} build-for-testing
  104 /usr/bin/tee #{SCREENSHOT_DERIVED_DATA_PATH}/build.log test-without-building
TABLE
selected_pids = targeted_screenshot_xcodebuild_pids(process_table)

$active_pids = []
$process_alive = {}
$terminated_pids = []
$cursor_count = 0

def targeted_screenshot_xcodebuild_pids(*)
  $active_pids.dup
end

def targeted_screenshot_process_alive?(pid)
  $process_alive.fetch(pid, false)
end

def terminate_targeted_screenshot_xcodebuild(pid, **)
  $terminated_pids << pid
  $process_alive[pid] = false
  $active_pids.delete(pid)
end

alias original_targeted_screenshot_log_cursor targeted_screenshot_log_cursor
def targeted_screenshot_log_cursor(log_path)
  $cursor_count += 1
  original_targeted_screenshot_log_cursor(log_path)
end

def wait_for_harness(timeout_seconds: 0.5)
  deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + timeout_seconds
  until yield
    raise "watchdog harness timed out" if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline

    sleep(0.002)
  end
end

first_pid_terminations = nil
prior_marker_terminations = nil
partial_marker_terminations = nil
elapsed = nil
Dir.mktmpdir("targeted-watchdog-test") do |directory|
  log_path = File.join(directory, "LaughTrack-LaughTrack.log")
  File.write(log_path, "")
  started_at = Process.clock_gettime(Process::CLOCK_MONOTONIC)
  with_targeted_screenshot_completion_watchdog(
    ["15_AuthenticatedFavorites", "16_Profile"],
    log_path: log_path,
    grace_seconds: 0.04,
    poll_interval: 0.002,
  ) do
    $process_alive[4242] = true
    $active_pids << 4242
    wait_for_harness { $cursor_count >= 1 }
    File.write(
      log_path,
      "Test Case '-[LaughTrackUITests.AppStoreScreenshotTests testGenerateAllScreenshots]' passed\n" \
      "snapshot: 15_AuthenticatedFavorites\n" \
      "snapshot: 16_Profile\n",
    )
    sleep(0.01)
    $process_alive[4242] = false
    $active_pids.delete(4242)
    sleep(0.01)
    first_pid_terminations = $terminated_pids.dup

    $process_alive[5252] = true
    $active_pids << 5252
    wait_for_harness { $cursor_count >= 2 }
    sleep(0.06)
    prior_marker_terminations = $terminated_pids.dup

    File.write(
      log_path,
      "Test Case '-[LaughTrackUITests.AppStoreScreenshotTests testGenerateAllScreenshots]' passed\n" \
      "snapshot: 15_AuthenticatedFavorites\n",
    )
    sleep(0.06)
    partial_marker_terminations = $terminated_pids.dup
    File.open(log_path, "a") { |file| file.write("snapshot: 16_Profile\n") }
    wait_for_harness { $terminated_pids.include?(5252) }
  end
  elapsed = Process.clock_gettime(Process::CLOCK_MONOTONIC) - started_at
end

puts JSON.generate(
  {
    "selected_pids" => selected_pids,
    "first_pid_terminations" => first_pid_terminations,
    "prior_marker_terminations" => prior_marker_terminations,
    "partial_marker_terminations" => partial_marker_terminations,
    "terminated_pids" => $terminated_pids,
    "cursor_count" => $cursor_count,
    "elapsed" => elapsed,
    "messages" => $messages,
  },
)
"""


def run_screenshot_lane(platform: str, mode: str, tmp_path: Path) -> list[str]:
    fastfile = REPO_ROOT / platform / "fastlane" / "Fastfile"
    result = subprocess.run(
        [
            "ruby",
            "-e",
            FASTFILE_HARNESS,
            str(fastfile),
            platform,
            str(tmp_path / platform / "run"),
            mode,
        ],
        cwd=fastfile.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def run_one_shot_launcher_harness() -> dict:
    fastfile = REPO_ROOT / "ios" / "fastlane" / "Fastfile"
    result = subprocess.run(
        ["ruby", "-e", ONE_SHOT_LAUNCHER_HARNESS, str(fastfile)],
        cwd=fastfile.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def run_watchdog_harness() -> dict:
    fastfile = REPO_ROOT / "ios" / "fastlane" / "Fastfile"
    result = subprocess.run(
        ["ruby", "-e", WATCHDOG_HARNESS, str(fastfile)],
        cwd=fastfile.parent,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_comparison_mode_collects_run_without_projecting_storefront(
    platform: str, tmp_path: Path
) -> None:
    events = run_screenshot_lane(platform, "comparison", tmp_path)
    assert [next(iter(event)) for event in events] == ["collect"]


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_default_mode_collects_run_and_projects_storefront(
    platform: str, tmp_path: Path
) -> None:
    events = run_screenshot_lane(platform, "export", tmp_path)
    assert [next(iter(event)) if isinstance(event, dict) else event for event in events] == ["collect", "project"]


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_targeted_mode_captures_selected_subset_without_projecting_storefront(
    platform: str, tmp_path: Path
) -> None:
    events = run_screenshot_lane(platform, "targeted", tmp_path)
    assert "project" not in events
    collect = next(event["collect"] for event in events if "collect" in event)
    assert collect["mode"] == "verification"
    assert collect["scenario_ids"] == [
        "02_SearchShows",
        "03_SearchComedians",
        "04_SearchClubs",
        "08_SearchPodcasts",
        "10_PodcastEpisodeDetail",
    ]
    capture = next(event["capture"] for event in events if "capture" in event)
    if platform == "ios":
        assert capture["clear_previous_screenshots"] is True
        assert capture["number_of_retries"] == 0
        assert capture["stop_after_first_error"] is True
        assert capture["launch_arguments"] == [
            "-UITestMockMode -ScreenshotScenarios "
            "02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts,"
            "10_PodcastEpisodeDetail -ScreenshotFixtureMode curated",
        ]
    else:
        assert capture["scenario_ids"] == collect["scenario_ids"]


def test_ios_targeted_favorites_capture_is_one_shot(tmp_path: Path) -> None:
    events = run_screenshot_lane("ios", "targeted_favorites", tmp_path)

    assert events.count("patch_targeted_snapshot_one_shot") == 1
    assert {"watchdog": ["15_AuthenticatedFavorites"]} in events
    capture = next(event["capture"] for event in events if isinstance(event, dict) and "capture" in event)
    collect = next(event["collect"] for event in events if isinstance(event, dict) and "collect" in event)
    assert capture["devices"] == ["iPhone 16 Pro Max"]
    assert capture["number_of_retries"] == 0
    assert capture["stop_after_first_error"] is True
    assert capture["launch_arguments"] == [
        "-UITestMockMode -ScreenshotScenarios 15_AuthenticatedFavorites "
        "-ScreenshotFixtureMode curated",
    ]
    assert collect["scenario_ids"] == ["15_AuthenticatedFavorites"]
    assert events.index("patch_targeted_snapshot_one_shot") < next(
        index for index, event in enumerate(events) if isinstance(event, dict) and "capture" in event
    )


def test_ios_targeted_one_shot_guard_skips_only_duplicate_launch_keys() -> None:
    result = run_one_shot_launcher_harness()

    assert result["duplicate_result"] is True
    assert [launch[:3] for launch in result["one_shot_launches"]] == [
        [["iPhone 16 Pro Max"], "en-US", None],
        [["iPad Pro 13-inch (M4)"], "en-US", None],
        [["iPhone 16 Pro Max"], "fr-FR", None],
    ]
    assert len(result["retryable_launches"]) == 2
    assert result["guard_ancestor_count"] == 1


def test_ios_targeted_watchdog_waits_for_complete_capture_then_terminates_exact_process() -> None:
    result = run_watchdog_harness()

    assert result["selected_pids"] == [101]
    assert result["first_pid_terminations"] == []
    assert result["prior_marker_terminations"] == []
    assert result["partial_marker_terminations"] == []
    assert result["terminated_pids"] == [5252]
    assert result["cursor_count"] == 2
    assert result["elapsed"] < 1
    assert any(
        "xcodebuild 5252 remained alive" in message for message in result["messages"]
    )


def test_ios_cold_cache_bootstraps_only_pinned_package_revisions(tmp_path: Path) -> None:
    events = run_screenshot_lane("ios", "cold", tmp_path)
    assert not any(isinstance(event, dict) and "watchdog" in event for event in events)
    run_tests_options = next(event["run_tests"] for event in events if isinstance(event, dict))
    capture_options = next(
        event["capture"]
        for event in events
        if isinstance(event, dict) and "capture" in event
    )

    assert run_tests_options["build_for_testing"] is True
    assert run_tests_options["skip_package_dependencies_resolution"] is False
    assert run_tests_options["disable_package_automatic_updates"] is True
    assert run_tests_options["skip_package_repository_fetches"] is True
    assert run_tests_options["derived_data_path"]
    assert "number_of_retries" not in capture_options
    assert "stop_after_first_error" not in capture_options


def test_regenerate_comparisons_requests_comparison_only_capture() -> None:
    script = (REPO_ROOT / "scripts" / "screenshots" / "regenerate-comparisons").read_text()

    assert script.index("prune-derived-data") < script.index(
        'echo "Capturing iOS comparison matrix..."'
    )
    assert 'ios_lane_args=(screenshots "run_root:$ios_run" comparison_only:true)' in script
    assert 'android_lane_args=(screenshots "run_root:$android_run" comparison_only:true)' in script
    assert script.count("--require-complete") == 2


def test_ios_search_capture_enters_the_real_tab_and_keeps_loaded_comedian_gates() -> None:
    source = (
        REPO_ROOT / "ios" / "Tests" / "LaughTrackUITests" / "AppStoreScreenshotTests.swift"
    ).read_text()

    assert 'relaunch(route: "search:0")' not in source
    search_relaunch = source.split("private func relaunchOnSearchTab() {", 1)[1].split(
        "\n    private func relaunch(", 1
    )[0]
    assert "relaunch()" in search_relaunch
    assert 'app.buttons["Search"].firstMatch' in search_relaunch
    assert "searchTab.tap()" in search_relaunch
    assert "Identifier.primitiveFilterScroller" in search_relaunch
    assert 'element("laughtrack.shows-search.screen")' in search_relaunch

    search_comedians = source.split('try runScenario("03_SearchComedians") {', 1)[1].split(
        'try runScenario("04_SearchClubs") {', 1
    )[0]
    assert (
        'assertFirstResult(identifierPrefix: "laughtrack.comedians-search.result-", '
        'description: "comedian")'
    ) in search_comedians
    assert (
        'captureSearch("03_SearchComedians", resultIdentifierPrefix: '
        '"laughtrack.comedians-search.result-", description: "comedian")'
    ) in search_comedians
