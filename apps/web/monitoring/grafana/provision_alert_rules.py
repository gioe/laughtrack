#!/usr/bin/env python3
"""Reconcile scraper-health-alerts.yaml into Grafana Cloud (TASK-3580).

Grafana Cloud has no file-based alert provisioning, so edits to a rule's
rawSql / threshold / states in scraper-health-alerts.yaml historically had to
be pushed by hand via the Alerting provisioning HTTP API (TASK-3577 did this
for 4 rules). This script makes the YAML the source of truth:

  - GET /api/v1/provisioning/alert-rules  (all live rules)
  - match each YAML rule to a live rule by uid, falling back to exact title
    (the live rules were created via the UI, so most carry random UIDs)
  - overlay the YAML-specified fields onto the live rule and PUT it back with
    X-Disable-Provenance if anything changed (no-op when already in sync)
  - POST rules that exist in the YAML but not in Grafana Cloud
  - reconcile each rule group's evaluation interval (the YAML `interval: 6h`
    vs whatever the group currently evaluates at)

Fields the YAML owns: title, condition, data (query/reduce/threshold chain),
noDataState, execErrState, for, labels, annotations, group interval.
Fields preserved from the live rule: uid, id, orgID, folderUID, ruleGroup,
isPaused, keep_firing_for, notification_settings (the "Discord Hook" receiver
binding lives only in Grafana), plus any server-added model defaults the YAML
does not specify (instant, intervalMs, sql editor scaffolding, ...).

contactPoints / policies blocks in the YAML are intentionally NOT reconciled —
the contact point holds a secret webhook URL placeholder and provisioned
policies would replace the org root policy tree (see the YAML comments).

Usage:
  GRAFANA_ACCOUNT_TOKEN=... python3 provision_alert_rules.py [--dry-run]

Options:
  --dry-run            report what would change without writing to Grafana
  --yaml PATH          alert-rules YAML (default: scraper-health-alerts.yaml
                       next to this script)
  --grafana-url URL    Grafana stack root (default: $GRAFANA_URL or
                       https://aiqobservability.grafana.net)

Exit codes: 0 = in sync (or successfully reconciled), 1 = error.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request

import yaml

try:  # macOS framework Pythons often lack system CA certs; GHA does not.
    import certifi

    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

DEFAULT_GRAFANA_URL = "https://aiqobservability.grafana.net"

# YAML rule fields overlaid onto the live rule. `data` and `for` get special
# handling (positional model merge / duration normalization) in build_desired.
SCALAR_FIELDS = ("title", "condition", "noDataState", "execErrState")
REPLACE_FIELDS = ("labels", "annotations")

_DURATION_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def parse_duration_seconds(value) -> int:
    """Parse a Grafana duration ('6h', '0m', '1h30m', bare seconds int)."""
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    total, matched = 0, False
    for num, unit in re.findall(r"(\d+)([smhd])", text):
        total += int(num) * _DURATION_UNITS[unit]
        matched = True
    if not matched:
        raise ValueError(f"unparseable duration: {value!r}")
    return total


class GrafanaClient:
    def __init__(self, base_url: str, token: str, dry_run: bool):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.dry_run = dry_run

    def _request(self, method: str, path: str, body=None):
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                # Keeps rules editable in the UI after an API write.
                "X-Disable-Provenance": "true",
            },
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            with urllib.request.urlopen(req, context=_SSL_CONTEXT) as resp:
                payload = resp.read()
        except urllib.error.HTTPError as err:
            detail = err.read().decode(errors="replace")
            raise RuntimeError(
                f"{method} {path} -> HTTP {err.code}: {detail}"
            ) from err
        return json.loads(payload) if payload else None

    def get(self, path: str):
        return self._request("GET", path)

    def write(self, method: str, path: str, body):
        if self.dry_run:
            return None
        return self._request(method, path, body)


def deep_merge(base, overlay):
    """Recursive dict merge: overlay wins; base keys absent in overlay survive.

    Lists and scalars are replaced wholesale by the overlay value.
    """
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        for key, value in overlay.items():
            merged[key] = deep_merge(base.get(key), value) if key in base else copy.deepcopy(value)
        return merged
    return copy.deepcopy(overlay)


def build_desired(live: dict, yaml_rule: dict) -> dict:
    """Overlay YAML-owned fields onto a copy of the live rule."""
    desired = copy.deepcopy(live)
    for field in SCALAR_FIELDS:
        if field in yaml_rule:
            desired[field] = yaml_rule[field]
    for field in REPLACE_FIELDS:
        if field in yaml_rule:
            desired[field] = copy.deepcopy(yaml_rule[field])
    if "for" in yaml_rule:
        # Grafana returns canonical Go durations ('0s'); compare semantically
        # and only rewrite when the YAML actually differs.
        if parse_duration_seconds(yaml_rule["for"]) != parse_duration_seconds(live.get("for", 0)):
            desired["for"] = str(yaml_rule["for"])
    # data: merge positionally so server-added model defaults (instant,
    # intervalMs, sql scaffolding) survive; the YAML chain length wins.
    live_data = live.get("data") or []
    desired["data"] = [
        deep_merge(live_data[i], _normalize_data_item(item, live_data[i]))
        if i < len(live_data)
        else _normalize_data_item(item, None)
        for i, item in enumerate(yaml_rule.get("data") or [])
    ]
    return desired


def _normalize_data_item(yaml_item: dict, live_item: dict | None) -> dict:
    """Adapt a YAML data item for the provisioning API.

    The file-provisioning format allows relativeTimeRange {from: 0, to: 0} on
    datasource queries, but the HTTP API rejects it ("invalid relative time
    range"). These are instant queries, so the range is inert: keep the live
    rule's accepted range, or default to {from: 600, to: 0} on creates.
    (Expression nodes are exempt from the validation and keep {0, 0}.)
    """
    item = copy.deepcopy(yaml_item)
    rtr = item.get("relativeTimeRange")
    if item.get("datasourceUid") != "__expr__" and rtr in (None, {"from": 0, "to": 0}):
        if live_item and live_item.get("relativeTimeRange"):
            item.pop("relativeTimeRange", None)  # preserve the live range
        else:
            item["relativeTimeRange"] = {"from": 600, "to": 0}
    return item


def changed_fields(live: dict, desired: dict) -> list[str]:
    return sorted(key for key in desired if desired.get(key) != live.get(key))


def new_rule_payload(yaml_rule: dict, folder_uid: str, group_name: str, sibling: dict | None) -> dict:
    payload = {
        "uid": yaml_rule["uid"],
        "orgID": 1,
        "folderUID": folder_uid,
        "ruleGroup": group_name,
        "title": yaml_rule["title"],
        "condition": yaml_rule["condition"],
        "data": [_normalize_data_item(item, None) for item in yaml_rule["data"]],
        "noDataState": yaml_rule.get("noDataState", "NoData"),
        "execErrState": yaml_rule.get("execErrState", "Error"),
        "for": str(yaml_rule.get("for", "0s")),
        "labels": yaml_rule.get("labels", {}),
        "annotations": yaml_rule.get("annotations", {}),
    }
    # Bind the same contact point as an existing rule in the group (the
    # receiver binding is Grafana-side state the YAML deliberately omits).
    if sibling and sibling.get("notification_settings"):
        payload["notification_settings"] = copy.deepcopy(sibling["notification_settings"])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--yaml",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper-health-alerts.yaml"),
    )
    parser.add_argument("--grafana-url", default=os.environ.get("GRAFANA_URL", DEFAULT_GRAFANA_URL))
    args = parser.parse_args()

    token = os.environ.get("GRAFANA_ACCOUNT_TOKEN")
    if not token:
        print("error: GRAFANA_ACCOUNT_TOKEN is not set", file=sys.stderr)
        return 1

    with open(args.yaml) as fh:
        spec = yaml.safe_load(fh)

    client = GrafanaClient(args.grafana_url, token, args.dry_run)
    live_rules = client.get("/api/v1/provisioning/alert-rules")
    by_uid = {rule["uid"]: rule for rule in live_rules}
    by_title = {rule["title"]: rule for rule in live_rules}

    prefix = "[dry-run] " if args.dry_run else ""
    updates = creates = errors = 0

    for group in spec.get("groups", []):
        group_name = group["name"]
        group_live = [r for r in live_rules if r.get("ruleGroup") == group_name]
        yaml_titles = {r["title"] for r in group.get("rules", [])}

        for yaml_rule in group.get("rules", []):
            uid, title = yaml_rule["uid"], yaml_rule["title"]
            live = by_uid.get(uid)
            if live is None:
                live = by_title.get(title)
                if live is not None:
                    print(f"note: '{title}' matched by title; live uid {live['uid']!r} != yaml uid {uid!r}")

            if live is None:
                folder_uid = group_live[0]["folderUID"] if group_live else None
                if folder_uid is None:
                    print(
                        f"error: cannot create '{title}': no existing rule in group "
                        f"'{group_name}' to take folderUID from. Create the group's "
                        "folder/first rule once via the UI, then re-run.",
                        file=sys.stderr,
                    )
                    errors += 1
                    continue
                payload = new_rule_payload(yaml_rule, folder_uid, group_name, group_live[0])
                print(f"{prefix}create: '{title}' (uid {uid}) in group '{group_name}'")
                try:
                    client.write("POST", "/api/v1/provisioning/alert-rules", payload)
                    creates += 1
                except RuntimeError as err:
                    print(f"error: create '{title}' failed: {err}", file=sys.stderr)
                    errors += 1
                continue

            desired = build_desired(live, yaml_rule)
            diff = changed_fields(live, desired)
            if not diff:
                print(f"in sync: '{title}' (uid {live['uid']})")
                continue
            print(f"{prefix}update: '{title}' (uid {live['uid']}) — changed: {', '.join(diff)}")
            try:
                client.write("PUT", f"/api/v1/provisioning/alert-rules/{live['uid']}", desired)
                updates += 1
            except RuntimeError as err:
                print(f"error: update '{title}' failed: {err}", file=sys.stderr)
                errors += 1

        for stray in group_live:
            if stray["title"] not in yaml_titles and stray["uid"] not in {r["uid"] for r in group.get("rules", [])}:
                print(f"warning: live rule '{stray['title']}' (uid {stray['uid']}) is not in the YAML — left untouched")

        # Group evaluation interval (e.g. TASK-3572's 6h Neon-cost cadence).
        if "interval" in group and group_live:
            folder_uid = group_live[0]["folderUID"]
            want = parse_duration_seconds(group["interval"])
            group_path = f"/api/v1/provisioning/folder/{folder_uid}/rule-groups/{group_name}"
            live_group = client.get(group_path)
            have = int(live_group.get("interval", 0))
            if have == want:
                print(f"in sync: group '{group_name}' interval ({want}s)")
            else:
                print(f"{prefix}update: group '{group_name}' interval {have}s -> {want}s")
                live_group["interval"] = want
                try:
                    client.write("PUT", group_path, live_group)
                    updates += 1
                except RuntimeError as err:
                    print(f"error: group '{group_name}' interval update failed: {err}", file=sys.stderr)
                    errors += 1

    print(f"{prefix}done: {updates} updated, {creates} created, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
