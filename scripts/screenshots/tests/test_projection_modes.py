import json
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]

FASTFILE_HARNESS = r"""
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
    {environment: {xcode: {}, simulator_runtime: {}}, version: "18.3.1", devices: {}}
  end

  def plan_ios_screenshot_cache(*)
    {"pending_profiles" => [], "reused_profiles" => [], "profile_fingerprints" => {}}
  end

  def validate_ios_screenshot_collection(*)
  end

  def collect_ios_screenshot_run(*)
    $events << "collect"
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

  def validate_screenshot_profile!(*)
  end

  def collect_android_screenshot_run(*)
    $events << "collect"
  end

  def export_play_projection(*)
    $events << "project"
  end
else
  raise "unknown platform"
end

options = {run_root: ARGV.fetch(2)}
options[:comparison_only] = true if ARGV.fetch(3) == "comparison"
$lanes.fetch(:screenshots).call(options)
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
    assert run_screenshot_lane(platform, "comparison", tmp_path) == ["collect"]


@pytest.mark.parametrize("platform", ["ios", "android"])
def test_default_mode_collects_run_and_projects_storefront(
    platform: str, tmp_path: Path
) -> None:
    assert run_screenshot_lane(platform, "export", tmp_path) == ["collect", "project"]


def test_regenerate_comparisons_requests_comparison_only_capture() -> None:
    script = (REPO_ROOT / "scripts" / "screenshots" / "regenerate-comparisons").read_text()

    assert 'ios_lane_args=(screenshots "run_root:$ios_run" comparison_only:true)' in script
    assert 'android_lane_args=(screenshots "run_root:$android_run" comparison_only:true)' in script
