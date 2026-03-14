# Prisma Migrations

> **Authoritative guide:** See [`../DEPLOYMENT.md` → Running Migrations](../DEPLOYMENT.md#running-migrations) for the full deployment workflow, including environment variable setup and post-migration data seeding.

---

## Production Database: Neon

This project uses [Neon](https://neon.tech) serverless PostgreSQL. There is no local database — all migrations target the Neon instance directly.

---

## Creating a New Migration

`prisma migrate dev` **cannot be used** in this project. The shadow database validation fails on a migration that requires existing data. Always write migrations manually.

### 1. Create the migration file

```
prisma/migrations/<timestamp>_<name>/migration.sql
```

Use the timestamp format `YYYYMMDDHHMMSS`:

```
prisma/migrations/20260304120000_add_missing_indexes/migration.sql
```

Write your SQL in that file (`CREATE INDEX`, `ALTER TABLE`, etc.).

### 2. Update `prisma/schema.prisma`

Reflect the schema change in the Prisma schema file so generated types stay in sync.

### 3. Commit both files

Commit the migration SQL and the updated schema together.

### 4. Apply via `prisma migrate deploy`

```bash
cd apps/web
npx prisma migrate deploy
```

Requires `DATABASE_URL` (pooled Neon endpoint) and `DIRECT_URL` (non-pooled Neon endpoint) in the environment. `DIRECT_URL` is required because the pooled endpoint blocks the advisory locks that migration tracking uses.

> **Timing:** Run `prisma migrate deploy` **before** the new app version goes live. Deploying code before the schema is updated will cause runtime errors.

---

## Rollback

If a migration needs to be reverted:

1. **Drop the objects** — run the inverse SQL manually (e.g. `DROP INDEX`, `DROP COLUMN`). Write it as a new migration file if you want it tracked.

2. **Destructive operations** (e.g. `DROP COLUMN`) cannot be rolled back without data loss. Back up the table first if there's any doubt.

---

## Why not `prisma migrate dev`?

The shadow database validation fails on migration `20260308000000_set_email_scraper_fields`, which contains a data-dependent operation requiring "Gotham Comedy Club" to exist. `prisma migrate dev` is blocked in all environments as a result. Use `prisma migrate deploy` exclusively.
