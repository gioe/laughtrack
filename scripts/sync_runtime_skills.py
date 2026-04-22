#!/usr/bin/env python3
"""Sync runtime-specific skill trees from the canonical Claude skill set.

This repo intentionally supports both Claude Code and Codex. The canonical skill
source lives in `.claude/skills/`; `.agents/skills/` is generated from it with a
small set of runtime-specific rewrites so the two trees do not drift by hand.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
AGENT_SKILLS = ROOT / ".agents" / "skills"
TUSK_MANIFEST = ROOT / ".claude" / "tusk-manifest.json"

TEXT_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (".Codex/skills/", ".agents/skills/"),
    (".Codex/skills", ".agents/skills"),
    (".claude/skills/", ".agents/skills/"),
    (".claude/skills", ".agents/skills"),
    ("CLAUDE.md", "AGENTS.md"),
    ("skill/CLAUDE.md", "skill/AGENTS.md"),
    ("Co-Authored-By: Claude ", "Co-Authored-By: Codex "),
    ("Playwright MCP", "the runtime's browser automation tooling"),
)

LINE_REPLACEMENTS = {
    "browser_navigate → <url>": "Use browser automation to navigate to `<url>`.",
    "browser_snapshot": "Inspect the rendered page to find the relevant navigation or embedded event data.",
    "browser_click → <events link ref>": "Open the discovered events page link.",
    "browser_network_requests": "Capture the page's network requests.",
}


CLAUDE_ONLY_FRONTMATTER_KEYS = {
    "allowed-tools",
    "trigger",
}


def _extract_frontmatter_keys(text: str) -> set[str]:
    if not text.startswith("---\n"):
        return set()

    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return set()

    keys: set[str] = set()
    for line in parts[1].splitlines():
        match = re.match(r"^([^:]+):\s*(.*)$", line)
        if match:
            keys.add(match.group(1).strip())
    return keys


def _transform_frontmatter_for_codex(text: str) -> str:
    if not text.startswith("---\n"):
        return text

    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return text

    _opening, frontmatter_block, body = parts
    filtered_lines: list[str] = []
    for line in frontmatter_block.splitlines():
        match = re.match(r"^([^:]+):\s*(.*)$", line)
        key = match.group(1).strip() if match else None
        if key in CLAUDE_ONLY_FRONTMATTER_KEYS:
            continue
        filtered_lines.append(line)

    return "---\n" + "\n".join(filtered_lines) + "\n---\n" + body


def _transform_text(text: str) -> str:
    for old, new in TEXT_REPLACEMENTS:
        text = text.replace(old, new)

    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        replacement = LINE_REPLACEMENTS.get(stripped)
        if replacement is None:
            lines.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        lines.append(f"{indent}{replacement}")

    text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return _transform_frontmatter_for_codex(text)


def _source_files() -> list[Path]:
    return sorted(path for path in CLAUDE_SKILLS.rglob("*") if path.is_file())


def _expected_agent_files() -> dict[Path, str]:
    expected: dict[Path, str] = {}
    for source in _source_files():
        rel = source.relative_to(CLAUDE_SKILLS)
        expected[AGENT_SKILLS / rel] = _transform_text(source.read_text(encoding="utf-8"))
    return expected


def sync_agent_skills() -> tuple[int, int, int]:
    expected = _expected_agent_files()
    written = 0
    removed = 0

    AGENT_SKILLS.mkdir(parents=True, exist_ok=True)

    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        path.write_text(content, encoding="utf-8")
        written += 1

    expected_paths = set(expected)
    for existing in sorted(path for path in AGENT_SKILLS.rglob("*") if path.is_file()):
        if existing in expected_paths:
            continue
        existing.unlink()
        removed += 1

    for directory in sorted((path for path in AGENT_SKILLS.rglob("*") if path.is_dir()), reverse=True):
        if any(directory.iterdir()):
            continue
        directory.rmdir()

    return len(expected), written, removed


def update_tusk_manifest() -> tuple[int, int]:
    try:
        existing = json.loads(TUSK_MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        existing = []

    skill_entries = sorted(
        f".claude/skills/{path.relative_to(CLAUDE_SKILLS).as_posix()}"
        for path in _source_files()
    )
    static_entries = [entry for entry in existing if not entry.startswith(".claude/skills/")]
    updated = sorted(dict.fromkeys(static_entries + skill_entries))

    if updated == existing:
        return len(updated), 0

    TUSK_MANIFEST.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    return len(updated), 1


def check() -> int:
    errors: list[str] = []
    expected = _expected_agent_files()

    for path, content in expected.items():
        if not path.exists():
            errors.append(f"missing generated skill file: {path.relative_to(ROOT)}")
            continue
        current = path.read_text(encoding="utf-8")
        if current != content:
            errors.append(f"stale generated skill file: {path.relative_to(ROOT)}")

    for existing in sorted(path for path in AGENT_SKILLS.rglob("*") if path.is_file()):
        if existing not in expected:
            errors.append(f"unexpected generated skill file: {existing.relative_to(ROOT)}")

    for path in sorted(AGENT_SKILLS.glob("*/SKILL.md")):
        keys = _extract_frontmatter_keys(path.read_text(encoding="utf-8"))
        disallowed = sorted(keys & CLAUDE_ONLY_FRONTMATTER_KEYS)
        if disallowed:
            joined = ", ".join(disallowed)
            errors.append(
                f"generated skill has Claude-only frontmatter ({joined}): {path.relative_to(ROOT)}"
            )

    try:
        manifest = json.loads(TUSK_MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append("missing .claude/tusk-manifest.json")
        manifest = []

    expected_skills = {
        f".claude/skills/{path.relative_to(CLAUDE_SKILLS).as_posix()}"
        for path in _source_files()
    }
    manifest_skills = {entry for entry in manifest if isinstance(entry, str) and entry.startswith(".claude/skills/")}

    for missing in sorted(expected_skills - manifest_skills):
        errors.append(f"manifest missing skill entry: {missing}")
    for extra in sorted(manifest_skills - expected_skills):
        errors.append(f"manifest has stale skill entry: {extra}")

    if not errors:
        print("Runtime skills are in sync.")
        return 0

    for error in errors:
        print(error, file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify sync state without writing files")
    args = parser.parse_args()

    if args.check:
        return check()

    count, written, removed = sync_agent_skills()
    manifest_count, manifest_written = update_tusk_manifest()
    print(f"Synced {count} skill files into .agents/skills ({written} written, {removed} removed).")
    if manifest_written:
        print(f"Updated .claude/tusk-manifest.json ({manifest_count} entries).")
    else:
        print(f".claude/tusk-manifest.json already current ({manifest_count} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
