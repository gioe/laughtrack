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
psql postgresql://<your_username>@localhost/<db_name> -f prisma/migrations/<timestamp>_<name>/migration.sql
```

Replace `<db_name>` with the local Supabase database name and `<your_username>` with your OS username. The superuser connection bypasses RLS and Supabase's schema restrictions.

### 3. Register in `_prisma_migrations`

After applying, tell Prisma the migration is done so it doesn't try to re-apply it:

First, compute the SHA-256 checksum of the migration file (Prisma validates this on `migrate status` / `migrate deploy`):

```bash
sha256sum prisma/migrations/<timestamp>_<name>/migration.sql
# On macOS: shasum -a 256 prisma/migrations/<timestamp>_<name>/migration.sql
```

Then insert the registration row using the computed checksum:

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
  '<sha256-checksum-from-above>',  -- must match; Prisma validates this
  now(),
  '<timestamp>_<name>',            -- must match the directory name exactly
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

## Deploying to Production (Neon)

Production uses Neon serverless. Prisma's standard `migrate deploy` works fine there because Neon doesn't have the internal schema drift that local Supabase does.

After applying the migration locally and committing it to the repo:

```bash
DATABASE_URL="<neon-connection-string>" npx prisma migrate deploy
```

This applies any unapplied migrations in `prisma/migrations/` in order. The migration you registered manually in the local `_prisma_migrations` table will also be registered in Neon automatically.

---

## Rollback

If a migration needs to be reverted:

1. **Drop the objects** — run the inverse SQL manually (e.g. `DROP INDEX`, `DROP COLUMN`, `DROP TABLE`). Write it in a new migration file if you want to track it.

2. **Remove the `_prisma_migrations` row**:

   ```sql
   DELETE FROM "_prisma_migrations" WHERE migration_name = '<timestamp>_<name>';
   ```

3. **Destructive operations** (e.g. `DROP COLUMN`) cannot be rolled back without data loss. Back up the table first if there's any doubt.

---

## Why not `prisma migrate dev`?

Supabase creates internal schemas (`auth`, `storage`, `realtime`, `pgbouncer`, etc.) that Prisma sees as drift. `prisma migrate dev` will prompt to reset the DB or fail. The manual workflow avoids touching Supabase internals entirely.
