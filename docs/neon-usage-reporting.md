# Neon Usage Reporting

Use `scripts/neon_usage_report.py` to inspect current Neon billing drivers without
manual Console inspection.

The script reads from Neon control-plane APIs only:

- Project consumption metrics:
  `GET https://console.neon.tech/api/v2/consumption_history/v2/projects`
- Project metadata:
  `GET https://console.neon.tech/api/v2/projects`
- Branch and endpoint inventory:
  `GET https://console.neon.tech/api/v2/projects/{project_id}/branches`
  and `GET https://console.neon.tech/api/v2/projects/{project_id}/endpoints`

Neon's consumption metrics API reports the usage-based billing line items for
compute, root-branch storage, child-branch storage, instant-restore history,
public and private network transfer, and extra branches. Neon documents that
calls to this API do not wake suspended computes, so the report is safe to run
for periodic polling.

Official references:

- <https://neon.com/docs/guides/consumption-metrics>
- <https://neon.com/docs/introduction/monitor-usage>
- <https://neon.com/docs/reference/api-reference>

## Requirements

Set these environment variables before running the report:

```bash
export NEON_API_KEY="<personal-or-org-api-key>"
export NEON_ORG_ID="<org-id>"
```

Optional:

```bash
export NEON_PROJECT_ID="<project-id>"
```

When `NEON_PROJECT_ID` is omitted, the script requests all projects available to
the organization. You can also pass one or more `--project-id` flags.

## Commands

Default: last 30 days at daily granularity.

```bash
make neon-usage
```

Explicit range:

```bash
python3 scripts/neon_usage_report.py \
  --from 2026-07-01T00:00:00Z \
  --to 2026-07-03T00:00:00Z \
  --granularity daily
```

Hourly report for the last 24 hours:

```bash
python3 scripts/neon_usage_report.py --granularity hourly
```

Consumption metrics only, without branch and endpoint inventory:

```bash
python3 scripts/neon_usage_report.py --no-inventory
```

## Output Sections

- `Compute`: `compute_unit_seconds` converted to CU-hours.
- `Storage`: `root_branch_bytes_month` and `child_branch_bytes_month`
  converted to GB-month.
- `PITR / Restore History`: `instant_restore_bytes_month` converted to
  GB-month.
- `Network Transfer`: `public_network_transfer_bytes` and
  `private_network_transfer_bytes` converted to GB.
- `Branch Costs`: `extra_branches_month`.
- `Branch Inventory`: current branch count, compute endpoint count, and per-branch
  endpoint attachment/state summary.

## Polling Guidance

Neon updates consumption data approximately every 15 minutes and recommends at
least 15 minutes between consumption API calls. For this project, use ad hoc
runs or schedule no more frequently than every 15 minutes.

Do not replace this with a direct database query for cost reporting. SQL queries
can wake a suspended compute; the Neon control-plane consumption endpoint is the
source that maps to usage-based billing and avoids compute wakeups.
