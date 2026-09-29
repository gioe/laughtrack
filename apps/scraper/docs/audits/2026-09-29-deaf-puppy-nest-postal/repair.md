# Production repair and rollback

Applied20260929200000_fill_deaf_puppy_nest_postal using locally pinned Prisma6
on2026-09-29, after confirming it was the only pending migration and no failed
migration remained. Actual row verification confirms551 empty string→95336 and
8713 null→43202. Every other club field and both complete source rows are identical.
All direct club/show foreign-key counts and fingerprints match the immediate
operation-before and after snapshots. Existing valid postal values were preserved.

The single atomic DO statement locks each target club and source, checks business,
address, coordinates, country, website and complete source config (excluding its
trigger-maintained updated_at), and only updates missing/blank ZIPs. Missing clubs
are no-ops in unrelated databases; identity/source drift aborts the entire statement.
A populated ZIP is never replaced, even if filled between audit and execution.

Production-shaped rollback-only validation found exactly two changed club rows,
with only zip_code different. All2884 other club rows and2760 populated postal
fields were unchanged. Replay is a no-op; inverse restores the exact original null
versus empty string. Trials reject both identity drift and source drift and verify
a changed second target rolls back the first target's update atomically. Populated
postal values on either target are preserved. Rollback refuses later postal edits.

rollback.sql is manual recovery only: it deliberately restores missing fields,
which would again exclude these venues from nearby ZIP discovery. It performs no
historical record deletion and preserves all other fields. Run inside an operator
transaction and inspect the two rows before commit. Because the forward migration
is already recorded in Prisma, rolling data back alone does not schedule reapplication.
