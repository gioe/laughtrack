"""Deterministic iOS simulator destination selection."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


@dataclass(frozen=True)
class Destination:
    name: str
    version: str
    udid: str


class DestinationNotFoundError(ValueError):
    """Raised when the requested simulator destination is unavailable."""


def _semantic_version(version: str) -> tuple[int, ...]:
    """Return a sortable numeric version tuple (for example, 18.6.1)."""
    match = re.fullmatch(r"\d+(?:\.\d+)*", version)
    if not match:
        return ()
    return tuple(int(component) for component in version.split("."))


def available_destinations(
    devices_payload: Mapping[str, Any], runtimes_payload: Mapping[str, Any]
) -> list[Destination]:
    """Join available devices to their runtime's exact semantic version."""
    runtime_versions = {
        runtime["identifier"]: runtime["version"]
        for runtime in runtimes_payload.get("runtimes", [])
        if runtime.get("isAvailable", True)
        and isinstance(runtime.get("identifier"), str)
        and isinstance(runtime.get("version"), str)
        and _semantic_version(runtime["version"])
    }

    destinations: list[Destination] = []
    for runtime_id, devices in devices_payload.get("devices", {}).items():
        version = runtime_versions.get(runtime_id)
        if version is None:
            continue
        for device in devices:
            if not device.get("isAvailable", True):
                continue
            name = device.get("name")
            udid = device.get("udid")
            if isinstance(name, str) and isinstance(udid, str):
                destinations.append(Destination(name=name, version=version, udid=udid))
    return destinations


def select_destination(
    devices_payload: Mapping[str, Any],
    runtimes_payload: Mapping[str, Any],
    *,
    model: str,
    ios_major: int,
    udid: str | None = None,
) -> Destination:
    """Select an exact model/major, preferring newest OS then stable UDID."""
    candidates = available_destinations(devices_payload, runtimes_payload)

    if udid is not None:
        matches = [candidate for candidate in candidates if candidate.udid == udid]
        request = f"UDID {udid}"
    else:
        matches = [
            candidate
            for candidate in candidates
            if candidate.name == model
            and _semantic_version(candidate.version)[0] == ios_major
        ]
        request = f"model {model!r} with iOS major {ios_major}"

    if not matches:
        listed = "\n".join(
            f"  - {candidate.name}, iOS {candidate.version}, UDID {candidate.udid}"
            for candidate in sorted(
                candidates,
                key=lambda item: (item.name, _semantic_version(item.version), item.udid),
            )
        )
        if not listed:
            listed = "  (no available iOS simulator devices)"
        raise DestinationNotFoundError(
            f"No available simulator matches requested {request}.\n"
            f"Available candidates:\n{listed}\n"
            "Install the requested runtime/device in Xcode Settings > Components, "
            "or override with --model/--ios-major (or TEST_SIM_NAME/TEST_IOS_MAJOR)."
        )

    newest_version = max(_semantic_version(candidate.version) for candidate in matches)
    newest_matches = [
        candidate
        for candidate in matches
        if _semantic_version(candidate.version) == newest_version
    ]
    return min(newest_matches, key=lambda item: item.udid)
