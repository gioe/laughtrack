# Prisma Migrations

## Local Dev DB (Supabase)

The local dev database is a Supabase instance. Running `prisma migrate dev` detects drift from Supabase internal schemas (`auth.*`, `storage.*`, `realtime.*`) and refuses to proceed.

Use the manual workflow below instead.

---

## Manual Migration Workflow

### 1. Create the migration file

```
prisma/migrations/<timestamp>_<name>/migration.sql
```

Use the same timestamp format as existing migrations: `YYYYMMDDHHMMSS`.

Example:
```
prisma/migrations/20260304120000_add_missing_indexes/migration.sql
```

Write your SQL in that file (e.g. `CREATE INDEX`, `ALTER TABLE`, etc.).

### 2. Apply via psql as superuser

```bash
psql postgresql://mattgioe@localhost/<db_name> -f prisma/migrations/<timestamp>_<name>/migration.sql
```

Replace `<db_name>` with the local Supabase database name. The superuser connection bypasses RLS and Supabase's schema restrictions.

### 3. Register in `_prisma_migrations`

After applying, tell Prisma the migration is done so it doesn't try to re-apply it:

```sql
INSERT INTO "_prisma_migrations" (
  id,
  checksum,
  finished_at,
  migration_name,
  logs,
  rolled_back_at,
  started_at,
  applied_steps_count
)
VALUES (
  gen_random_uuid(),
  '',                          -- leave blank; Prisma won't re-check this
  now(),
  '<timestamp>_<name>',        -- must match the directory name exactly
  NULL,
  NULL,
  now(),
  1
);
```

Run this against the same local DB.

### 4. Verify

```bash
npx prisma migrate status
```

The migration should appear as **Applied**.

---

## Why not `prisma migrate dev`?

Supabase creates internal schemas (`auth`, `storage`, `realtime`, `pgbouncer`, etc.) that Prisma sees as drift. `prisma migrate dev` will prompt to reset the DB or fail. The manual workflow avoids touching Supabase internals entirely.
