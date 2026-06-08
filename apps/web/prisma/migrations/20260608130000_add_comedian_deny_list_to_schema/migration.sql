-- Align Prisma schema with the existing prod comedian_deny_list table.
--
-- The table was created on the scraper side via raw SQL in
-- apps/scraper/migrations/20260323_add_comedian_deny_list.sql (TASK-641) and
-- holds ~2,500 rows in prod. It was never modeled in schema.prisma, so the
-- sql-parse-time guard (apps/scraper/tests/sql/test_sql_parse_time.py) xfailed
-- the two queries that reference it (GET_DENIED_NAMES, UPSERT_DENY_LIST_NAMES).
-- The deny-list is the documented residual orphan filter per
-- docs/comedian-visible-consolidation.md Decision 1 — covers names that have
-- never been ingested, complementing comedians.visible=false (TASK-2713).
--
-- IF NOT EXISTS makes this migration a no-op on environments that already
-- have the table (prod, any DB whose history includes the scraper migration).
-- On a fresh DB the table is created with the same column shape as prod.
-- Functional equivalence is preserved: name is NOT NULL and unique either as
-- the prod UNIQUE constraint or the Prisma-generated PRIMARY KEY.

CREATE TABLE IF NOT EXISTS "comedian_deny_list" (
    "name" TEXT NOT NULL,
    "reason" TEXT NOT NULL DEFAULT '',
    "deleted_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "added_by" TEXT NOT NULL DEFAULT 'audit_script',

    CONSTRAINT "comedian_deny_list_pkey" PRIMARY KEY ("name")
);
