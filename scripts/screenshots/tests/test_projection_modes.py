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
if ARGV.fetch(3) == "targeted"
  options[:profiles] = ARGV.fetch(1) == "ios" ? "ios_phone,ios_large_tablet" : "android_phone"
  options[:scenarios] = "02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts,10_PodcastEpisodeDetail"
  $lanes.fetch(:verify_screenshots).call(options)
else
  $lanes.fetch(:screenshots).call(options)
end
puts JSON.generate($events)
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
        assert capture["launch_arguments"] == [
            "-UITestMockMode -ScreenshotScenarios "
            "02_SearchShows,03_SearchComedians,04_SearchClubs,08_SearchPodcasts,"
            "10_PodcastEpisodeDetail -ScreenshotFixtureMode curated",
        ]
    else:
        assert capture["scenario_ids"] == collect["scenario_ids"]


def test_ios_cold_cache_bootstraps_only_pinned_package_revisions(tmp_path: Path) -> None:
    events = run_screenshot_lane("ios", "cold", tmp_path)
    run_tests_options = next(event["run_tests"] for event in events if isinstance(event, dict))

    assert run_tests_options["build_for_testing"] is True
    assert run_tests_options["skip_package_dependencies_resolution"] is False
    assert run_tests_options["disable_package_automatic_updates"] is True
    assert run_tests_options["skip_package_repository_fetches"] is True
    assert run_tests_options["derived_data_path"]


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
