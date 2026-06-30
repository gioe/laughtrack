import { PGlite } from "@electric-sql/pglite";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";

const HERE = dirname(fileURLToPath(import.meta.url));

function loadMigrationSql(): string {
    const migrationsDir = resolve(HERE, "migrations");
    const suffix = "_add_youtube_live_notifications";
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

const SCHEMA_TEXT = readFileSync(resolve(HERE, "schema.prisma"), "utf-8");
const MIGRATION_SQL = loadMigrationSql();

const BASE_SCHEMA_SQL = `
    CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE
    );

    CREATE TABLE comedians (
        uuid TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );
`;

async function expectRejects(db: PGlite, sql: string, params: unknown[] = []) {
    await expect(db.query(sql, params)).rejects.toThrow();
}

describe("YouTube live notification schema", () => {
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
        await db.exec(
            "TRUNCATE youtube_live_notifications, comedians, users RESTART IDENTITY CASCADE",
        );
    });

    it("defines canonical comedian channel IDs and a dedicated YouTube live notification model", () => {
        expect(SCHEMA_TEXT).toContain(
            'youtubeChannelId                     String?                           @map("youtube_channel_id")',
        );
        expect(SCHEMA_TEXT).toContain("model YouTubeLiveNotification");
        expect(SCHEMA_TEXT).toContain('@@map("youtube_live_notifications")');
        expect(MIGRATION_SQL).toMatch(
            /ALTER TABLE comedians\s+ADD COLUMN youtube_channel_id TEXT/,
        );
        expect(MIGRATION_SQL).toContain(
            "CREATE INDEX comedians_youtube_channel_id_idx",
        );
        expect(MIGRATION_SQL).toContain(
            "CREATE TABLE youtube_live_notifications",
        );
    });

    it("enforces one send per user, comedian, video, and notification type", async () => {
        await db.query("INSERT INTO users (id, email) VALUES ($1, $2)", [
            "user-1",
            "fan@example.com",
        ]);
        await db.query("INSERT INTO comedians (uuid, name) VALUES ($1, $2)", [
            "comedian-1",
            "Live Comic",
        ]);

        const insert = `
            INSERT INTO youtube_live_notifications (
                user_id,
                comedian_id,
                youtube_channel_id,
                youtube_video_id,
                video_title,
                video_url,
                notification_type
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        `;

        await db.query(insert, [
            "user-1",
            "comedian-1",
            "UC123",
            "video-1",
            "Live Stream",
            "https://www.youtube.com/watch?v=video-1",
            "push",
        ]);
        await expectRejects(db, insert, [
            "user-1",
            "comedian-1",
            "UC123",
            "video-1",
            "Live Stream",
            "https://www.youtube.com/watch?v=video-1",
            "push",
        ]);
        await db.query(insert, [
            "user-1",
            "comedian-1",
            "UC123",
            "video-1",
            "Live Stream",
            "https://www.youtube.com/watch?v=video-1",
            "email",
        ]);

        const result = await db.query<{ count: string }>(
            "SELECT COUNT(*) FROM youtube_live_notifications",
        );
        expect(Number(result.rows[0].count)).toBe(2);
    });
});
