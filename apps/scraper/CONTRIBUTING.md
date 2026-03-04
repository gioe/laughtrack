# Contributing to the Scraper

## Logging Convention: `print()` vs `Logger`

This codebase intentionally uses both `print()` and `Logger` — they serve distinct purposes and both are correct.

| Use | When |
|-----|------|
| `print()` | User-facing terminal output: menus, prompts, formatted tables. Must reach the user's terminal regardless of the configured log level. `Logger.info` is silently dropped at the default WARNING console level, so interactive output **must** use `print()`. |
| `Logger` | Machine-readable telemetry: structured events, errors, progress markers written to log files or consumed by log aggregators. Use `Logger` for anything that should appear in log files or be monitored programmatically. |

**Rule of thumb:**
- User sees it → `print()`
- Log file / monitoring sees it → `Logger`
- User-facing *error feedback* that also belongs in log files → `Logger.warning` / `Logger.error` is acceptable (these surface on the terminal at the default WARNING level)

Future Logger-migration tasks must **not** require that all `print()` calls be removed from interactive CLI code — doing so would break user-facing menus and prompts.

### Worked Example

See [`src/laughtrack/utilities/domain/club/selector.py`](src/laughtrack/utilities/domain/club/selector.py) for a concrete example of a module that correctly mixes both — `print()` for menu rendering and `Logger` for structured event emission.
