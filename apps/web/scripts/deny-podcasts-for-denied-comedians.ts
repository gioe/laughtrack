import { neonConfig } from "@neondatabase/serverless";
import type { PrismaClient } from "@prisma/client";
import { WebSocket } from "ws";
import type { denyPodcastsHostedByComedianName as DenyHostedPodcastsFn } from "../lib/admin/podcastDenyList";

type CandidateRow = {
    comedian_name: string;
    podcast_id: number;
    title: string;
    source: string;
    source_podcast_id: string;
    feed_url: string | null;
};

type DenyListNameRow = {
    name: string;
};

function hasFlag(flag: string): boolean {
    return process.argv.includes(flag);
}

async function listCandidates(): Promise<CandidateRow[]> {
    return db.$queryRaw<CandidateRow[]>`
        SELECT DISTINCT
            c.name AS comedian_name,
            p.id AS podcast_id,
            p.title,
            p.source,
            p.source_podcast_id,
            p.feed_url
        FROM comedian_deny_list dl
        JOIN comedians c
          ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
             lower(btrim(regexp_replace(replace(dl.name, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
        JOIN comedian_podcasts cp ON cp.comedian_id = c.id
        JOIN podcasts p ON p.id = cp.podcast_id
        WHERE cp.review_status = 'accepted'
          AND cp.association_type IN ('host', 'cohost')
          AND NOT EXISTS (
              SELECT 1
              FROM podcast_deny_list pdl
              WHERE pdl.restored_at IS NULL
                AND (
                    pdl.podcast_id = p.id
                    OR (pdl.source = p.source AND pdl.source_podcast_id = p.source_podcast_id)
                    OR (p.feed_url IS NOT NULL AND pdl.feed_url = p.feed_url)
                )
          )
        ORDER BY c.name ASC, p.title ASC, p.id ASC
    `;
}

let db: PrismaClient;

async function configureDatabase() {
    neonConfig.webSocketConstructor = WebSocket;

    const dbModule = await import("../lib/db");
    db = dbModule.db;
    const helperModule = await import("../lib/admin/podcastDenyList");
    return helperModule.denyPodcastsHostedByComedianName as typeof DenyHostedPodcastsFn;
}

async function main() {
    const apply = hasFlag("--apply");
    const denyPodcastsHostedByComedianName = await configureDatabase();
    const candidates = await listCandidates();

    if (!apply) {
        console.log(
            JSON.stringify(
                {
                    mode: "dry-run",
                    candidateCount: candidates.length,
                    candidates,
                    nextStep:
                        "Run bin/deny-podcasts-for-denied-comedians --apply to write podcast_deny_list rows.",
                },
                null,
                2,
            ),
        );
        return;
    }

    const names = await db.$queryRaw<DenyListNameRow[]>`
        SELECT DISTINCT dl.name
        FROM comedian_deny_list dl
        JOIN comedians c
          ON lower(btrim(regexp_replace(replace(c.name, chr(160), ' '), '[[:space:]]+', ' ', 'g'))) =
             lower(btrim(regexp_replace(replace(dl.name, chr(160), ' '), '[[:space:]]+', ' ', 'g')))
        JOIN comedian_podcasts cp ON cp.comedian_id = c.id
        WHERE cp.review_status = 'accepted'
          AND cp.association_type IN ('host', 'cohost')
        ORDER BY dl.name ASC
    `;

    const denied = await db.$transaction(async (tx) => {
        const results = [];
        for (const row of names) {
            const deniedPodcasts = await denyPodcastsHostedByComedianName(tx, {
                comedianName: row.name,
                reason: `Host comedian is on comedian deny list: ${row.name}`,
                deniedBy: "script:deny-podcasts-for-denied-comedians",
            });
            results.push({ comedianName: row.name, deniedPodcasts });
        }
        return results;
    });

    console.log(
        JSON.stringify(
            {
                mode: "apply",
                candidateCountBeforeApply: candidates.length,
                deniedPodcastCount: denied.reduce(
                    (sum, row) => sum + row.deniedPodcasts.length,
                    0,
                ),
                denied,
            },
            null,
            2,
        ),
    );
}

main()
    .catch((error) => {
        console.error(error);
        process.exitCode = 1;
    })
    .finally(async () => {
        await db.$disconnect();
    });
