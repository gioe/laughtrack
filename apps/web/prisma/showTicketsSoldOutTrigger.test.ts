import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

// Integration test for the tickets -> shows.tickets_sold_out trigger added in
// the `_add_show_tickets_sold_out` migration. Runs the real SQL against PGlite
// so the plpgsql functions, row triggers, TRUNCATE trigger, and one-shot
// backfill are exercised end-to-end.

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_show_tickets_sold_out";
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

async function readTicketsSoldOut(
    db: PGlite,
    showId: number,
): Promise<boolean> {
    const res = await db.query<{ tickets_sold_out: boolean }>(
        "SELECT tickets_sold_out FROM shows WHERE id = $1",
        [showId],
    );
    return res.rows[0].tickets_sold_out;
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
    soldOut: boolean,
): Promise<number> {
    const res = await db.query<{ id: number }>(
        "INSERT INTO tickets (show_id, sold_out) VALUES ($1, $2) RETURNING id",
        [showId, soldOut],
    );
    return res.rows[0].id;
}

describe("tickets_trickle_show_tickets_sold_out trigger", () => {
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

    it("keeps shows with no tickets available", async () => {
        const showId = await createShow(db);

        expect(await readTicketsSoldOut(db, showId)).toBe(false);
    });

    it("sets tickets_sold_out true only when every ticket is sold out", async () => {
        const showId = await createShow(db);

        const available = await insertTicket(db, showId, false);
        await insertTicket(db, showId, true);
        expect(await readTicketsSoldOut(db, showId)).toBe(false);

        await db.query("UPDATE tickets SET sold_out = true WHERE id = $1", [
            available,
        ]);
        expect(await readTicketsSoldOut(db, showId)).toBe(true);
    });

    it("returns to false when one ticket becomes available", async () => {
        const showId = await createShow(db);
        const ticketId = await insertTicket(db, showId, true);
        await insertTicket(db, showId, true);
        expect(await readTicketsSoldOut(db, showId)).toBe(true);

        await db.query("UPDATE tickets SET sold_out = false WHERE id = $1", [
            ticketId,
        ]);
        expect(await readTicketsSoldOut(db, showId)).toBe(false);
    });

    it("recomputes both shows when a ticket moves between shows", async () => {
        const showA = await createShow(db);
        const showB = await createShow(db);
        const ticketId = await insertTicket(db, showA, true);
        await insertTicket(db, showB, false);
        expect(await readTicketsSoldOut(db, showA)).toBe(true);
        expect(await readTicketsSoldOut(db, showB)).toBe(false);

        await db.query("UPDATE tickets SET show_id = $1 WHERE id = $2", [
            showB,
            ticketId,
        ]);
        expect(await readTicketsSoldOut(db, showA)).toBe(false);
        expect(await readTicketsSoldOut(db, showB)).toBe(false);
    });

    it("sets tickets_sold_out false when the last ticket is deleted", async () => {
        const showId = await createShow(db);
        const ticketId = await insertTicket(db, showId, true);
        expect(await readTicketsSoldOut(db, showId)).toBe(true);

        await db.query("DELETE FROM tickets WHERE id = $1", [ticketId]);
        expect(await readTicketsSoldOut(db, showId)).toBe(false);
    });

    it("refreshes all shows after ticket table truncation", async () => {
        const showId = await createShow(db);
        await insertTicket(db, showId, true);
        expect(await readTicketsSoldOut(db, showId)).toBe(true);

        await db.exec("TRUNCATE tickets");
        expect(await readTicketsSoldOut(db, showId)).toBe(false);
    });
});

describe("one-shot tickets_sold_out backfill", () => {
    let db: PGlite;

    beforeAll(async () => {
        db = new PGlite();
        await db.exec(BASE_SCHEMA_SQL);
        await db.exec(`
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO shows DEFAULT VALUES;
            INSERT INTO tickets (show_id, sold_out) VALUES
                (1, true),
                (1, true),
                (2, true),
                (2, false);
        `);
        await db.exec(MIGRATION_SQL);
    });

    afterAll(async () => {
        await db.close();
    });

    it("backfills true for shows whose existing tickets are all sold out", async () => {
        expect(await readTicketsSoldOut(db, 1)).toBe(true);
    });

    it("backfills false for mixed or empty ticket sets", async () => {
        expect(await readTicketsSoldOut(db, 2)).toBe(false);
        expect(await readTicketsSoldOut(db, 3)).toBe(false);
    });
});
