from pathlib import Path
import shutil, subprocess, tempfile, json

root = Path(__file__).resolve().parents[3]
harness = r"""
require 'json'
$lanes = {}; $events = []
def default_platform(*); end
def platform(*); yield; end
def before_all(*); end
def desc(*); end
def lane(name, &block); $lanes[name] = block; end
module UI
 def self.success(*); end
 def self.user_error!(message); raise message; end
end
load ARGV.fetch(0)
def read_project_yml_setting(*); '2.25.0'; end
[:screenshots, :bump_build_number, :build, :upload_app_store, :tag_release, :load_asc_api_key].each do |name|
 define_method(name) { |*args, **kwargs| $events << name.to_s }
end
def generate_release_notes(**kwargs)
 $events << 'generate_release_notes'
 $lanes[:generate_release_notes].call(kwargs)
end
def deliver(**options); $events << options; end
begin
 $lanes[ARGV.fetch(1).to_sym].call(JSON.parse(ARGV.fetch(2), symbolize_names: true))
 puts JSON.generate(events: $events)
rescue => e
 puts JSON.generate(events: $events, error: e.message)
end
"""


def test_release_metadata_gates_and_upload_options():
    with tempfile.TemporaryDirectory() as temp:
        repo = Path(temp)
        ff = repo / "ios/fastlane/Fastfile"
        ff.parent.mkdir(parents=True)
        shutil.copy(root / "ios/fastlane/Fastfile", ff)
        (repo / "screenshots").mkdir()
        shutil.copy(
            root / "screenshots/catalog.json", repo / "screenshots/catalog.json"
        )
        (ff.parent / "release_notes").mkdir()
        (ff.parent / "metadata/en-US").mkdir(parents=True)
        (ff.parent / "release_notes/2.25.0.txt").write_text(
            "Reviewed podcast discovery notes.\n"
        )

        def run(lane, options):
            return json.loads(
                subprocess.check_output(
                    ["ruby", "-e", harness, str(ff), lane, json.dumps(options)],
                    text=True,
                )
            )

        result = run("beta", {"bump": "minor"})
        assert "2.26.0.txt" in result["error"] and result["events"] == [
            "generate_release_notes"
        ], result
        result = run("beta", {"skip_marketing_bump": True})
        assert result["events"] == [
            "generate_release_notes",
            "screenshots",
            "bump_build_number",
            "build",
            "upload_app_store",
            "tag_release",
        ], result
        assert (
            ff.parent / "metadata/en-US/release_notes.txt"
        ).read_text() == "Reviewed podcast discovery notes.\n"
        result = run("upload_app_store", {})
        assert result["events"][-1]["overwrite_screenshots"] is True, result
        result = run("upload_metadata", {})
        assert (
            result["events"][-1]["overwrite_screenshots"] is True
            and result["events"][-1]["skip_binary_upload"] is True
        ), result
        for version in ["../2.25.0", "9.9.9"]:
            assert "error" in run("generate_release_notes", {"version": version})
        (ff.parent / "release_notes/2.25.0.txt").write_text(" ")
        assert "error" in run("generate_release_notes", {})
        (ff.parent / "release_notes/2.25.0.txt").write_text("x" * 4001)
        assert "error" in run("generate_release_notes", {})
