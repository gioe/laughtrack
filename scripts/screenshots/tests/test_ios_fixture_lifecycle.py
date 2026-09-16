"""Exercise the real Fastfile fixture process around both simulator test lanes."""

import json
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
FASTFILE = REPO_ROOT / "ios" / "fastlane" / "Fastfile"

LIFECYCLE_HARNESS = r"""
require "json"
require "net/http"
require "socket"

$lanes = {}
$events = []
$spawned = []

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
$verbose_before = $VERBOSE
$VERBOSE = nil
reservation = TCPServer.new("127.0.0.1", 0)
Object.const_set(:SCREENSHOT_FIXTURE_PORT, reservation.addr[1])
Object.const_set(:SCREENSHOT_FIXTURE_SERVER_PATH, ARGV[5]) if ARGV[5]
$VERBOSE = $verbose_before

$scenario = ARGV.fetch(2)
reservation.close unless $scenario == "busy"
ENV["LAUGHTRACK_SCREENSHOT_FIXTURE_PORT"] = ARGV.fetch(3) == "unset" ? nil : "previous-port"
ENV["LAUGHTRACK_SCREENSHOT_FIXTURE_LOG"] = ARGV.fetch(4)
ENV["IOS26_SIMULATOR_UDID"] = "watcher-selected-udid"

module RecordFixtureSpawn
  def spawn(*arguments, **options)
    super.tap { |pid| $spawned << pid }
  end
end
Process.singleton_class.prepend(RecordFixtureSpawn)

def run_tests(**options)
  port = ENV.fetch("LAUGHTRACK_SCREENSHOT_FIXTURE_PORT")
  uri = URI("http://127.0.0.1:#{port}/fixture/status")
  response = Net::HTTP.start(uri.host, uri.port, nil, open_timeout: 1, read_timeout: 1) do |http|
    http.get(uri.request_uri)
  end
  $events << ["run_tests", options, port, JSON.parse(response.body)]
  raise "synthetic run_tests failure" if $scenario == "failure"
end

error = nil
begin
  $lanes.fetch(ARGV.fetch(1).to_sym).call
rescue => caught
  error = {"class" => caught.class.name, "message" => caught.message}
end

listening = begin
  TCPSocket.open("127.0.0.1", SCREENSHOT_FIXTURE_PORT, &:close)
  true
rescue SystemCallError
  false
end

children_reaped = $spawned.all? do |pid|
  begin
    Process.waitpid(pid, Process::WNOHANG)
    false
  rescue Errno::ECHILD
    true
  end
end

puts JSON.generate({
  "events" => $events,
  "error" => error,
  "port" => SCREENSHOT_FIXTURE_PORT,
  "restored_port" => ENV["LAUGHTRACK_SCREENSHOT_FIXTURE_PORT"],
  "listening_after_lane" => listening,
  "spawned_count" => $spawned.length,
  "children_reaped" => children_reaped,
  "log_exists" => File.file?(ENV.fetch("LAUGHTRACK_SCREENSHOT_FIXTURE_LOG")),
})
reservation.close unless reservation.closed?
"""


def run_lane(
    tmp_path: Path, lane: str, scenario: str, previous_port: str,
    server_script: Path | None = None,
) -> dict:
    result = subprocess.run(
        [
            "ruby", "-e", LIFECYCLE_HARNESS, str(FASTFILE), lane, scenario,
            previous_port, str(tmp_path / "fixture.log"),
            *([str(server_script)] if server_script else []),
        ],
        cwd=FASTFILE.parent,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("lane", ["test", "test_ios26_watch"])
@pytest.mark.parametrize("scenario", ["success", "failure"])
@pytest.mark.parametrize("previous_port", ["unset", "set"])
def test_lanes_own_ready_fixture_and_cleanup_on_every_exit(
    tmp_path: Path, lane: str, scenario: str, previous_port: str,
) -> None:
    result = run_lane(tmp_path, lane, scenario, previous_port)

    runs = [event for event in result["events"] if event[0] == "run_tests"]
    assert len(runs) == 1
    _, options, port, contract = runs[0]
    assert port == str(result["port"])
    assert contract["mode"] == "curated"
    assert contract["result_count"] > 0
    assert len(contract["fingerprint"]) == 64
    assert options["parallel_testing"] is False
    if lane == "test_ios26_watch":
        assert options["destination"] == "platform=iOS Simulator,id=watcher-selected-udid"
    else:
        assert "OS=18." in options["destination"]
    assert result["restored_port"] == (None if previous_port == "unset" else "previous-port")
    assert result["spawned_count"] == 1
    assert result["children_reaped"]
    assert not result["listening_after_lane"]
    assert result["log_exists"]
    assert result["error"] == (
        {"class": "RuntimeError", "message": "synthetic run_tests failure"}
        if scenario == "failure" else None
    )


@pytest.mark.parametrize("lane", ["test", "test_ios26_watch"])
def test_busy_port_refuses_tests_without_touching_external_listener(
    tmp_path: Path, lane: str,
) -> None:
    result = run_lane(tmp_path, lane, "busy", "set")

    assert result["error"] is not None
    assert not any(event[0] == "run_tests" for event in result["events"])
    assert result["spawned_count"] == 0
    assert result["restored_port"] == "previous-port"
    assert result["listening_after_lane"]


@pytest.mark.parametrize("scenario", ["exits_early", "wrong_contract"])
def test_startup_failure_never_runs_tests_and_cleans_up(
    tmp_path: Path, scenario: str,
) -> None:
    server_script = tmp_path / "unready_fixture.py"
    if scenario == "exits_early":
        server_script.write_text("raise SystemExit('synthetic startup failure')\n")
    else:
        server_script.write_text(
            "import sys\n"
            "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
            "class Handler(BaseHTTPRequestHandler):\n"
            "    def do_GET(self):\n"
            "        self.send_response(200)\n"
            "        self.end_headers()\n"
            "        self.wfile.write(b'{\"mode\":\"unrelated-server\"}')\n"
            "    def log_message(self, *args):\n"
            "        pass\n"
            "HTTPServer(('127.0.0.1', int(sys.argv[-1])), Handler).serve_forever()\n"
        )
    result = run_lane(tmp_path, "test_ios26_watch", scenario, "set", server_script)

    assert not any(event[0] == "run_tests" for event in result["events"])
    assert result["error"]["class"] == "RuntimeError"
    expected_message = "exited early" if scenario == "exits_early" else "did not become ready"
    assert expected_message in result["error"]["message"]
    assert result["spawned_count"] == 1
    assert result["children_reaped"]
    assert not result["listening_after_lane"]
    assert result["restored_port"] == "previous-port"
    assert result["log_exists"]


def test_watcher_workflow_uses_fixture_owning_lane_and_selected_simulator() -> None:
    workflow = (REPO_ROOT / ".github/workflows/ios.yml").read_text()
    watcher_step = workflow.split(
        "      - name: Run tests on the iOS 26.x simulator (watcher)\n", 1,
    )[1].split("\n      - name:", 1)[0]

    assert "bundle exec fastlane test_ios26_watch" in watcher_step
    assert "bundle exec fastlane scan" not in watcher_step
    assert "IOS26_SIMULATOR_UDID: ${{ steps.ios26_simulator.outputs.udid }}" in watcher_step
    assert "LAUGHTRACK_SCREENSHOT_FIXTURE_LOG:" in watcher_step
