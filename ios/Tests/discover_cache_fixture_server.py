#!/usr/bin/env python3
"""Deterministic Discover launch/refresh fixture for NavigationTransitionUITests.

From the repository root, run in separate terminals:
    python3 ios/Tests/discover_cache_fixture_server.py
    ios/bin/test-sim LaughTrackUITests/NavigationTransitionUITests/testDiscoverDiskCacheSurvivesPendingAndFailedRefresh
Uses the canonical screenshot payloads; the only extension is HTTP lifecycle control.
"""
import argparse
import socket
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "screenshots"))
from fixture_server import API_PREFIX, FixtureHandler, FixtureState, ThreadingHTTPServer, fixture_response


class ControlledServer(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, ControlledHandler)
        self.fixture_state = FixtureState()
        self.lock = threading.Lock()
        self.gate = None
        self.failure = False
        self.pending = 0
        self.revision = 0


class ControlledHandler(FixtureHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        server = self.server
        if path.startswith("/fixture/feed/"):
            action = path.rsplit("/", 1)[-1]
            with server.lock:
                if action == "block":
                    if server.gate is not None:
                        server.gate.set()
                    server.gate = threading.Event()
                    server.failure = False
                elif action in {"ready", "release", "fail"}:
                    server.failure = action == "fail"
                    if not server.failure:
                        server.revision += 1
                    if server.gate is not None:
                        server.gate.set()
                    server.gate = None
                elif action != "status":
                    self._write_json(400, {"error": "unknown feed control"})
                    return
                result = {"pending": server.pending, "revision": server.revision}
            self._write_json(200, result)
            return
        if path == f"{API_PREFIX}home/feed":
            with server.lock:
                gate = server.gate
                server.pending += 1
            try:
                if gate is not None and not gate.wait(timeout=60):
                    self._write_json(504, {"error": "fixture gate timed out"})
                    return
                with server.lock:
                    failure = server.failure
                    revision = server.revision
                if failure:
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    self.connection.close()
                else:
                    host = self.headers.get("Host", f"127.0.0.1:{server.server_port}")
                    payload = fixture_response(path, f"http://{host}", server.fixture_state.current_mode())
                    payload["data"]["trendingThisWeek"][0]["name"] = f"Cache edition {revision}"
                    payload["data"]["railPlan"] = {
                        "version": 1, "catalogVersion": 2, "policyVersion": 3,
                        "platform": "ios", "cycleIndex": 0,
                        "rails": [
                            {"railKey": key, "payloadKey": field, "position": index,
                             "itemIds": [str(item["id"]) for item in payload["data"][field]]}
                            for index, (key, field) in enumerate([
                                ("shows_tonight", "showsTonight"),
                                ("trending_this_week", "trendingThisWeek"),
                                ("trending_comedians", "trendingComedians"),
                                ("popular_clubs", "popularClubs"),
                            ])
                        ],
                    }
                    self._write_json(200, payload)
            finally:
                with server.lock:
                    server.pending -= 1
            return
        super().do_GET()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with ControlledServer(("127.0.0.1", args.port)) as server:
        print(f"Discover cache fixture listening on {args.port}", flush=True)
        server.serve_forever()
