"""Unified CLI entry point for laughtrack scraper commands.

Usage:
    python -m laughtrack.app.cli <command> [args...]

Commands:
    audit-show    Dry-run lineup comparison for a specific show.
    manage-subscriptions  Manage email subscription tracking for clubs.

Run any command with --help for full usage details.
"""

from __future__ import annotations

import sys

_COMMANDS = {
    "audit-show": "laughtrack.app.commands.audit_show",
    "manage-subscriptions": "laughtrack.app.commands.manage_subscriptions",
}

_HELP = {
    "audit-show": "Dry-run lineup comparison for a specific show.",
    "manage-subscriptions": "Manage email subscription tracking for clubs.",
}


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print("usage: laughtrack.app.cli <command> [args...]\n")
        print("Commands:")
        for name, desc in _HELP.items():
            print(f"  {name:<26}{desc}")
        print("\nRun any command with --help for full usage details.")
        sys.exit(0)

    command = args[0]
    if command not in _COMMANDS:
        print(f"error: unknown command '{command}'", file=sys.stderr)
        print(f"Available commands: {', '.join(_COMMANDS)}", file=sys.stderr)
        sys.exit(2)

    import importlib
    mod = importlib.import_module(_COMMANDS[command])
    mod.main(sys.argv[2:])


if __name__ == "__main__":
    main()
