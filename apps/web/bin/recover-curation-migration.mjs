#!/usr/bin/env node
// One-time recovery for the known, transactionally rolled-back club migration.
// Default is read-only; --apply resolves only that exact failed attempt.
import { PrismaClient } from "@prisma/client";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const migration = "20261015120000_club_curation_intake";
const web = fileURLToPath(new URL("../", import.meta.url));
const db = new PrismaClient();
try {
  const failed = await db.$queryRawUnsafe(
    `SELECT migration_name,logs,applied_steps_count FROM _prisma_migrations WHERE finished_at IS NULL AND rolled_back_at IS NULL`,
  );
  if (!failed.length) {
    console.log("No unresolved failed migrations; recovery is unnecessary.");
  } else {
    if (
      failed.length !== 1 ||
      failed[0].migration_name !== migration ||
      failed[0].applied_steps_count !== 0 ||
      !failed[0].logs?.includes("42703") ||
      !failed[0].logs?.includes(
        'column "visible" of relation "shows" does not exist',
      )
    ) {
      throw new Error(
        "Unexpected migration failure; refusing automatic recovery.",
      );
    }
    const source = readFileSync(
      new URL(
        `../prisma/migrations/${migration}/migration.sql`,
        import.meta.url,
      ),
      "utf8",
    );
    const names = [
      ...source.matchAll(/CREATE (?:OR REPLACE )?FUNCTION (\w+)/g),
    ].map((match) => match[1]);
    const remaining = await db.$queryRawUnsafe(
      `SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=current_schema() AND p.proname=ANY($1::text[])`,
      names,
    );
    if (!names.length || remaining.length)
      throw new Error(
        "Club migration DDL remains installed; reconcile partial state before recovery.",
      );
    console.log(
      "Verified exact shows.visible failure, zero applied steps, and all club functions rolled back.",
    );
    if (process.argv.includes("--apply")) {
      const result = spawnSync(
        process.execPath,
        [
          "node_modules/prisma/build/index.js",
          "migrate",
          "resolve",
          "--rolled-back",
          migration,
        ],
        { cwd: web, env: process.env, stdio: "inherit" },
      );
      if (result.status !== 0)
        throw new Error("Prisma migration recovery failed.");
    } else
      console.log(
        "Read-only preflight passed. Use --apply to mark the failed attempt rolled back, then prisma migrate deploy.",
      );
  }
} finally {
  await db.$disconnect();
}
