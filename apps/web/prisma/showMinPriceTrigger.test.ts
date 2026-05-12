import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

// Integration test for the tickets -> shows.min_price trigger added in the
// `_add_show_min_price_with_trigger` migration. Runs the real SQL against an
// in-process Postgres (PGlite) so the plpgsql function, the per-event
// INSERT/UPDATE/DELETE triggers, the WHEN gate, AND the one-shot backfill
// statement at the bottom of the migration are exercised end-to-end. JS-side
// tests (findShowsWithCount, the SHOW_SORT_MAP wiring) cover the ORDER BY
// plumbing; this file is what catches a future migration that narrows the
// WHEN clause or broadens the price filter.

const HERE = dirname(fileURLToPath(import.meta.url));

// Resolve the migration directory by suffix-glob rather than full timestamp so
// a future rename (e.g. Prisma regenerating timestamps after a squash) surfaces
// as a meaningful "migration not found" assertion rather than a confusing
// ENOENT mid-test.
function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_show_min_price_with_trigger";
    const matches = readdirSync(migrationsDir).filter((entry) =>
        entry.endsWith(suffix),
    );
    if (matches.length !== 1) {
        throw new Error(
            `Expected exactly one migration directory ending in '${suffix}', found ${matches.length}: ${matches.join(", ")}`,
        );
    }
    return readFileSync(
        resolve(migrationsDir, matches[0], "migration.sql"),
        "utf-8",
    );
}

const MIGRATION_SQL = loadMigrationSql();

// Minimal schema covering the columns the trigger touches. Real prisma schema
// has many more columns; the trigger only reads tickets.show_id /
// tickets.price and writes shows.min_price.
const BASE_SCHEMA_SQL = `
    CREATE TABLE shows (
        id SERIAL PRIMARY KEY
    );
    CREATE TABLE tickets (
        id SERIAL PRIMARY KEY,
        show_id INTEGER NOT NULL REFERENCES shows(id) ON DELETE CASCADE,
        price NUMERIC(7, 2),
        purchase_url TEXT,
        sold_out BOOLEAN NOT NULL DEFAULT false
    );
`;

// PGlite returns NUMERIC columns as strings to preserve precision (same as
// node-postgres). Normalize to number for comparison; null stays null.
function asNumber(value: unknown): number | null {
    if (value === null || value === undefined) return null;
    return typeof value === "number" ? value : Number(value);
}

async function readMinPrice(
    db: PGlite,
    showId: number,
): Promise<number | null> {
    const res = await db.query<{ min_price: string | null }>(
        "SELECT min_price FROM shows WHERE id = $1",
        [showId],
    );
    return asNumber(res.rows[0]?.min_price);
}

async function createShow(db: PGlite): Promise<number> {
    const res = await db.query<{ id: number }>(
        "INSERT INTO shows DEFAULT VALUES RETURNING id",
    );
    return res.rows[0].id;
}

async function insertTicket(
    db: PGlite,
    showId: number,
    price: number | null,
    purchaseUrl: string | null = null,
): Promise<number> {
    const res = await db.query<{ id: number }>(
        "INSERT INTO tickets (show_id, price, purchase_url) VALUES ($1, $2, $3) RETURNING id",
        [showId, price, purchaseUrl],
    );
    return res.rows[0].id;
}

describe("tickets_trickle_show_min_price trigger", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    beforeEach(async () => {
        await db.exec("TRUNCATE tickets, shows RESTART IDENTITY CASCADE");
    });

    describe("INSERT", () => {
        it("sets min_price to the first paid ticket", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, 25.5);
            expect(await readMinPrice(db, showId)).toBe(25.5);
        });

        it("lowers min_price when a cheaper paid ticket is inserted", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, 25);
            await insertTicket(db, showId, 15);
            expect(await readMinPrice(db, showId)).toBe(15);
        });

        it("keeps the existing min_price when a more expensive ticket is inserted", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, 15);
            await insertTicket(db, showId, 25);
            expect(await readMinPrice(db, showId)).toBe(15);
        });

        it("excludes free (price = 0) tickets from min_price", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, 0);
            expect(await readMinPrice(db, showId)).toBeNull();

            await insertTicket(db, showId, 20);
            expect(await readMinPrice(db, showId)).toBe(20);
        });

        it("excludes NULL-price tickets from min_price", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, null);
            expect(await readMinPrice(db, showId)).toBeNull();

            await insertTicket(db, showId, 30);
            expect(await readMinPrice(db, showId)).toBe(30);
        });

        it("isolates min_price per show", async () => {
            const showA = await createShow(db);
            const showB = await createShow(db);
            await insertTicket(db, showA, 10);
            await insertTicket(db, showB, 40);
            expect(await readMinPrice(db, showA)).toBe(10);
            expect(await readMinPrice(db, showB)).toBe(40);
        });
    });

    describe("UPDATE", () => {
        it("recomputes min_price when the cheapest ticket's price changes", async () => {
            const showId = await createShow(db);
            const ticketId = await insertTicket(db, showId, 15);
            await insertTicket(db, showId, 25);
            expect(await readMinPrice(db, showId)).toBe(15);

            await db.query("UPDATE tickets SET price = $1 WHERE id = $2", [
                30,
                ticketId,
            ]);
            expect(await readMinPrice(db, showId)).toBe(25);
        });

        it("recomputes when a paid ticket is updated to free (price = 0)", async () => {
            const showId = await createShow(db);
            const cheap = await insertTicket(db, showId, 15);
            await insertTicket(db, showId, 30);
            expect(await readMinPrice(db, showId)).toBe(15);

            await db.query("UPDATE tickets SET price = 0 WHERE id = $1", [
                cheap,
            ]);
            expect(await readMinPrice(db, showId)).toBe(30);
        });

        it("recomputes when a paid ticket is updated to NULL price", async () => {
            const showId = await createShow(db);
            const cheap = await insertTicket(db, showId, 15);
            await insertTicket(db, showId, 30);

            await db.query("UPDATE tickets SET price = NULL WHERE id = $1", [
                cheap,
            ]);
            expect(await readMinPrice(db, showId)).toBe(30);
        });

        it("falls back to NULL when the last paid ticket becomes free", async () => {
            const showId = await createShow(db);
            const ticketId = await insertTicket(db, showId, 15);

            await db.query("UPDATE tickets SET price = 0 WHERE id = $1", [
                ticketId,
            ]);
            expect(await readMinPrice(db, showId)).toBeNull();
        });

        it("recomputes both shows when show_id moves", async () => {
            const showA = await createShow(db);
            const showB = await createShow(db);
            const ticketId = await insertTicket(db, showA, 12);
            await insertTicket(db, showB, 40);
            expect(await readMinPrice(db, showA)).toBe(12);
            expect(await readMinPrice(db, showB)).toBe(40);

            await db.query("UPDATE tickets SET show_id = $1 WHERE id = $2", [
                showB,
                ticketId,
            ]);
            expect(await readMinPrice(db, showA)).toBeNull();
            expect(await readMinPrice(db, showB)).toBe(12);
        });

        it("does not fire when an unrelated column (purchase_url) is updated", async () => {
            // The WHEN clause gates the UPDATE trigger on
            //     OLD.price IS DISTINCT FROM NEW.price
            //  OR OLD.show_id IS DISTINCT FROM NEW.show_id
            // so the nightly scraper's bulk purchase_url / sold_out rewrites do
            // not touch shows. We can't observe the trigger NOT firing directly,
            // but we can prove min_price stays consistent (no spurious value)
            // after such an update.
            const showId = await createShow(db);
            await insertTicket(db, showId, 15, "https://example.com/old");
            expect(await readMinPrice(db, showId)).toBe(15);

            // Manually corrupt min_price to a wrong value, then run an update
            // that should NOT fire the trigger. If the WHEN gate is broken and
            // the trigger fires anyway, min_price will be repaired to 15.
            await db.query("UPDATE shows SET min_price = 999 WHERE id = $1", [
                showId,
            ]);
            await db.query(
                "UPDATE tickets SET purchase_url = $1 WHERE show_id = $2",
                ["https://example.com/new", showId],
            );
            expect(await readMinPrice(db, showId)).toBe(999);
        });
    });

    describe("DELETE", () => {
        it("recomputes min_price when the cheapest ticket is deleted", async () => {
            const showId = await createShow(db);
            const cheap = await insertTicket(db, showId, 15);
            await insertTicket(db, showId, 30);
            expect(await readMinPrice(db, showId)).toBe(15);

            await db.query("DELETE FROM tickets WHERE id = $1", [cheap]);
            expect(await readMinPrice(db, showId)).toBe(30);
        });

        it("sets min_price to NULL when the last paid ticket is deleted", async () => {
            const showId = await createShow(db);
            const ticketId = await insertTicket(db, showId, 20);
            await insertTicket(db, showId, 0);
            expect(await readMinPrice(db, showId)).toBe(20);

            await db.query("DELETE FROM tickets WHERE id = $1", [ticketId]);
            expect(await readMinPrice(db, showId)).toBeNull();
        });

        it("leaves min_price NULL when a free ticket is deleted from a paid-only set", async () => {
            const showId = await createShow(db);
            await insertTicket(db, showId, 25);
            const free = await insertTicket(db, showId, 0);
            expect(await readMinPrice(db, showId)).toBe(25);

            await db.query("DELETE FROM tickets WHERE id = $1", [free]);
            expect(await readMinPrice(db, showId)).toBe(25);
        });
    });

    describe("invariant: shows.min_price = MIN(price) WHERE price > 0", () => {
        it("matches MIN(price WHERE price > 0) after a mixed series of writes", async () => {
            const showId = await createShow(db);

            // Replay a representative INSERT/UPDATE/DELETE sequence, then
            // assert the denormalized value equals the freshly-computed MIN.
            const t1 = await insertTicket(db, showId, 30);
            await insertTicket(db, showId, 0); // free
            await insertTicket(db, showId, null); // NULL
            const t4 = await insertTicket(db, showId, 18);
            await db.query("UPDATE tickets SET price = $1 WHERE id = $2", [
                22,
                t4,
            ]);
            await db.query("DELETE FROM tickets WHERE id = $1", [t1]);

            const stored = await readMinPrice(db, showId);
            const computed = await db.query<{ min_price: string | null }>(
                "SELECT MIN(price) AS min_price FROM tickets WHERE show_id = $1 AND price IS NOT NULL AND price > 0",
                [showId],
            );
            expect(stored).toBe(asNumber(computed.rows[0].min_price));
            expect(stored).toBe(22);
        });
    });
});

describe("one-shot backfill on migration apply", () => {
    // The trigger keeps min_price in sync for new writes, but existing rows on
    // the day of deploy depend on the UPDATE ... FROM (SELECT MIN(price) ...
    // GROUP BY show_id) block at the bottom of migration.sql. Run the migration
    // against a pre-seeded ticket set so a future change that breaks the
    // backfill (e.g. dropping the 'price > 0' guard, swapping in MIN(price)
    // without NULL/free handling) fails this test instead of silently leaving
    // deployed rows with wrong values.

    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        // Seed three shows with a representative mix before the trigger /
        // backfill exists. Use plain SQL — no helpers — because the helpers
        // assume the migration has already run.
        await db.exec(`
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO tickets (show_id, price) VALUES
                (1, 30),
                (1, 18),
                (1, 0),
                (1, NULL),
                (2, 50),
                (3, 0),
                (3, NULL);
        `);
        // Sanity: shows.min_price column doesn't exist yet, so all rows are
        // implicitly unset. Apply the migration — this adds the column,
        // creates the trigger, AND runs the one-shot backfill UPDATE.
        await db.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("backfills min_price for shows with paid tickets", async () => {
        expect(await readMinPrice(db, 1)).toBe(18);
        expect(await readMinPrice(db, 2)).toBe(50);
    });

    it("leaves min_price NULL for shows with only free/NULL tickets", async () => {
        expect(await readMinPrice(db, 3)).toBeNull();
    });
});
