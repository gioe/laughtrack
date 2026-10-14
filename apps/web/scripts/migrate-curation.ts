import { createHash } from "node:crypto";
import { Prisma } from "@prisma/client";
import { readFileSync } from "node:fs";
import { neonConfig } from "@neondatabase/serverless";
import { WebSocket } from "ws";
import {
    planMigration,
    inspectMigration,
    applyMigration,
} from "../lib/admin/curation/migration";
import {
    migrationCompatibility,
    restoreImportedDecision,
} from "../lib/admin/curation/migrationCompatibility";
import type { Store } from "../lib/admin/curation/decisions";
const args = process.argv.slice(2);
const value = (flag: string) => {
    const i = args.indexOf(flag);
    return i < 0 ? undefined : args[i + 1];
};
async function main() {
    if (!process.env.DATABASE_URL)
        throw new Error(
            "Set DATABASE_URL explicitly; this tool does not choose a production database.",
        );
    const url = new URL(process.env.DATABASE_URL);
    const databaseFingerprint = createHash("sha256")
        .update(`${url.hostname}:${url.port}${url.pathname}`)
        .digest("hex");
    neonConfig.webSocketConstructor = WebSocket;
    const { db } = await import("../lib/db");
    const store: Store = {
        $queryRaw: (q) => db.$queryRaw(q),
        $transaction: (fn) =>
            db.$transaction((tx) => fn(tx), { timeout: 60000 }),
    };
    try {
        const apply = args.includes("--apply"),
            actor = value("--actor"),
            restore = value("--restore");
        if (restore) {
            const relationship = value("--target") === "relationship";
            const result = apply
                ? await restoreImportedDecision(store, {
                      id: restore,
                      relationship,
                      expectedVersion: Number(value("--expected-version")),
                      actor,
                      reason: value("--reason"),
                  })
                : await migrationCompatibility(store, restore, relationship);
            console.log(
                JSON.stringify(
                    { mode: apply ? "restore" : "restore-preview", result },
                    null,
                    2,
                ),
            );
            return;
        }
        if (apply) {
            if (!value("--plan") || !actor)
                throw new Error(
                    "Apply requires --plan <reviewed JSON file> and --actor <operator>.",
                );
            const saved = JSON.parse(readFileSync(value("--plan")!, "utf8"));
            if (saved.databaseFingerprint !== databaseFingerprint)
                throw new Error(
                    "Plan belongs to another database connection. Generate a fresh dry run for this destination.",
                );
            const result = await applyMigration(
                store,
                saved.plan ?? saved,
                actor,
            );
            console.log(JSON.stringify({ mode: "apply", result }, null, 2));
        } else {
            const result = await store.$transaction(async (tx) => {
                await tx.$queryRaw(
                    Prisma.sql`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY`,
                );
                const plan = await planMigration(tx, {
                    source: value("--source"),
                    environment: value("--environment"),
                    after: value("--after") ?? "",
                    limit: Number(value("--limit") ?? 10),
                });
                return {
                    mode: "dry-run",
                    databaseFingerprint,
                    plan,
                    reconciliation: await inspectMigration(tx, plan),
                };
            });
            console.log(JSON.stringify(result, null, 2));
        }
    } finally {
        await db.$disconnect();
    }
}
main().catch((error) => {
    console.error(
        error instanceof Error ? error.message : "Curation migration failed",
    );
    process.exitCode = 1;
});
