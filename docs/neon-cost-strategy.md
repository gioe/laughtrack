# Neon Cost Strategy

This policy keeps LaughTrack's Neon usage predictable while preserving the
ability to verify code against realistic data.

Official Neon references:

- Branches are copy-on-write, isolated from their parent, and can be deleted
  when no longer needed: <https://neon.com/docs/introduction/branching>
- Temporary branches can have an expiration timestamp and are deleted
  permanently with their compute endpoints when they expire:
  <https://neon.com/docs/guides/branch-expiration>
- Inactive computes scale to zero after 5 minutes by default and wake on the
  next query: <https://neon.com/docs/introduction/scale-to-zero>
- Cost drivers include compute, root and child branch storage, restore history,
  extra branches, and data transfer:
  <https://neon.com/docs/introduction/cost-optimization>
- The history window controls instant-restore retention and its storage cost:
  <https://neon.com/docs/introduction/history-window>

## Default Posture

- Keep production on the root production branch. Do not use the production
  branch for destructive manual testing, migration rehearsal, bulk backfills, or
  scraper experiments.
- Keep development and preview branches temporary. Every non-production branch
  needs an owner and either an expiration timestamp or a tracked cleanup action.
- Keep scale-to-zero enabled for every non-production compute. A suspended
  compute still retains storage, but it stops accruing active compute time until
  the next query.
- Keep the project history window at the shortest value that satisfies recovery
  needs. A longer history window increases retained WAL history and cost.
- Monitor cost with `docs/neon-usage-reporting.md` before adding long-lived
  branches, increasing the history window, adding read replicas, or disabling
  scale-to-zero.

## Local Development

`apps/web/bin/dev` intentionally assembles `DATABASE_URL` from
`apps/scraper/.env` and can point the local app at Neon. This is acceptable for
read-only verification against live inventory, but it is not a general local
write sandbox.

Use the production Neon branch only for:

- read-only page rendering and visual verification;
- read-only SQL inspection;
- reproducing production-only query plans with `EXPLAIN` or
  `EXPLAIN ANALYZE` when the query is not mutating state;
- validating that existing production rows are displayed or filtered correctly.

Use a Neon child branch instead for:

- `prisma migrate deploy` rehearsal;
- any data-modifying local testing;
- bulk repair scripts, scraper writes, cleanup scripts, and backfills;
- tests that create, update, delete, truncate, or otherwise mutate tables;
- any investigation where a mistaken click in the local UI could alter
  production data.

If production Neon is used locally, treat the warning from `apps/web/bin/dev` as
binding: avoid admin actions, destructive flows, and scripts that write through
the app. When a task needs write verification, create a child branch and point
`apps/scraper/.env` or the command environment at that branch's connection
components for the duration of the task.

## Preview and CI Branches

The existing `web-ci.yml` migration job creates an ephemeral Neon branch from
production, applies pending Prisma migrations to that branch, and deletes the
branch in an `always()` cleanup step. Keep that pattern for automated migration
validation because it tests real production-shaped data without mutating
production.

For any new automated preview or CI branch:

- name it with enough context to identify the owner and source run, for example
  `ci-migrations-<run_id>-<attempt>` or `preview-<pr_number>-<sha>`;
- set an expiration timestamp when the creating tool supports it;
- delete it explicitly at the end of the workflow even when expiration is set;
- keep branch computes on scale-to-zero;
- avoid attaching scheduled jobs or persistent clients that keep the compute
  awake.

Recommended TTLs:

| Branch type                              | TTL                                              | Owner                    |
| ---------------------------------------- | ------------------------------------------------ | ------------------------ |
| CI migration rehearsal                   | 2-4 hours                                        | GitHub Actions workflow  |
| Vercel or PR preview                     | 24-48 hours after last deploy                    | PR owner                 |
| Local feature branch with write testing  | 1-7 days                                         | Developer who created it |
| Long-running staging or test environment | Explicit task or incident owner, reviewed weekly | Infrastructure           |

Branches that exceed their TTL without a current owner should be deleted, not
renamed or left idle.

## Scale-to-Zero Policy

Keep scale-to-zero enabled for all local, preview, CI, and staging computes.
The cold-start cost is acceptable for these environments, and Neon wakes the
compute automatically on the next query.

Production may disable scale-to-zero only when user-facing cold starts or
background jobs justify always-on compute. Before disabling it on production,
check current usage in the Neon Console or with `make neon-usage` and record the
reason in the task or incident that made the change.

Do not add scheduled pings to keep non-production computes warm. Pings defeat
the cost-control purpose of scale-to-zero and can turn a temporary branch into
continuous compute usage.

## Manual Neon Console Steps

No repository configuration change is required for TASK-3571. The recommended
controls are Neon project settings and branch lifecycle operations:

1. Confirm non-production computes have scale-to-zero enabled.
2. Confirm the production history window matches the current recovery target.
   Use the shortest window that satisfies rollback needs.
3. When manually creating temporary branches, leave automatic deletion enabled
   or set an explicit expiration timestamp.
4. Review the branch list weekly. Delete ownerless branches, expired previews,
   and local feature branches that are no longer tied to an active task.
5. Use `make neon-usage` before and after branch lifecycle changes when cost is
   the reason for the change.

## Cleanup Ownership

- GitHub Actions owns branches it creates and must delete them in the workflow.
- Vercel or PR preview branch cleanup is owned by the PR owner unless a managed
  integration deletes the branch automatically.
- Local development branches are owned by the developer who created them.
- Infrastructure owns weekly inventory review and any project-wide settings
  changes such as history-window adjustments or production scale-to-zero.

When ownership is unclear, Infrastructure is responsible for either deleting the
branch or assigning a new owner with an expiration date.
