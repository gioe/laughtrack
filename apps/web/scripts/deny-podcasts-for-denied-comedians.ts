import { neonConfig } from "@neondatabase/serverless";
import type { Prisma, PrismaClient } from "@prisma/client";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { WebSocket } from "ws";

export type CandidateRow = {
    comedian_names: string[];
    podcast_id: number;
    title: string;
    source: string;
    source_podcast_id: string;
    feed_url: string | null;
};

type AppliedRow = {
    podcast_id: number;
};

type QueryClient = Pick<Prisma.TransactionClient, "$queryRaw">;
type BackfillClient = Pick<PrismaClient, "$queryRaw" | "$transaction">;

export type PodcastDenyBackfillResult = {
    mode: "dry-run" | "apply";
    candidateCount: number;
    deniedPodcastCount: number;
    candidates: CandidateRow[];
    denied: CandidateRow[];
};

function hasFlag(flag: string): boolean {
    return process.argv.includes(flag);
}

export async function listCandidates(
    client: QueryClient,
): Promise<CandidateRow[]> {
    return client.$queryRaw<CandidateRow[]>`
        SELECT
            array_agg(DISTINCT dl.name ORDER BY dl.name) AS comedian_names,
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
        GROUP BY
            p.id,
            p.title,
            p.source,
            p.source_podcast_id,
            p.feed_url
        ORDER BY p.title ASC, p.id ASC
    `;
}

async function applyCandidate(
    client: QueryClient,
    candidate: CandidateRow,
): Promise<boolean> {
    const reason = `Host comedian is on comedian deny list: ${candidate.comedian_names.join(", ")}`;
    const deniedBy = "script:deny-podcasts-for-denied-comedians";

    const rows = await client.$queryRaw<AppliedRow[]>`
        WITH matched_restored AS (
            SELECT pdl.id
            FROM podcast_deny_list pdl
            WHERE pdl.restored_at IS NOT NULL
              AND (
                  pdl.podcast_id = ${candidate.podcast_id}
                  OR (
                      pdl.source = ${candidate.source}
                      AND pdl.source_podcast_id = ${candidate.source_podcast_id}
                  )
                  OR (
                      ${candidate.feed_url} IS NOT NULL
                      AND pdl.feed_url = ${candidate.feed_url}
                  )
              )
            ORDER BY
                CASE WHEN pdl.podcast_id = ${candidate.podcast_id} THEN 0 ELSE 1 END,
                pdl.id ASC
            LIMIT 1
            FOR UPDATE
        ),
        reactivated AS (
            UPDATE podcast_deny_list pdl
            SET reason = ${reason},
                denied_at = NOW(),
                denied_by = ${deniedBy},
                restored_at = NULL,
                restored_by = NULL,
                updated_at = NOW()
            WHERE pdl.id IN (SELECT id FROM matched_restored)
              AND pdl.restored_at IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM podcast_deny_list active
                  WHERE active.restored_at IS NULL
                    AND (
                        active.podcast_id = ${candidate.podcast_id}
                        OR (
                            active.source = ${candidate.source}
                            AND active.source_podcast_id = ${candidate.source_podcast_id}
                        )
                        OR (
                            ${candidate.feed_url} IS NOT NULL
                            AND active.feed_url = ${candidate.feed_url}
                        )
                    )
              )
            RETURNING ${candidate.podcast_id}::integer AS podcast_id
        ),
        inserted AS (
            INSERT INTO podcast_deny_list (
                podcast_id,
                source,
                source_podcast_id,
                feed_url,
                reason,
                denied_by
            )
            SELECT
                ${candidate.podcast_id},
                ${candidate.source},
                ${candidate.source_podcast_id},
                ${candidate.feed_url},
                ${reason},
                ${deniedBy}
            WHERE NOT EXISTS (SELECT 1 FROM reactivated)
              AND NOT EXISTS (
                  SELECT 1
                  FROM podcast_deny_list active
                  WHERE active.restored_at IS NULL
                    AND (
                        active.podcast_id = ${candidate.podcast_id}
                        OR (
                            active.source = ${candidate.source}
                            AND active.source_podcast_id = ${candidate.source_podcast_id}
                        )
                        OR (
                            ${candidate.feed_url} IS NOT NULL
                            AND active.feed_url = ${candidate.feed_url}
                        )
                    )
              )
            ON CONFLICT DO NOTHING
            RETURNING podcast_id
        )
        SELECT podcast_id FROM reactivated
        UNION ALL
        SELECT podcast_id FROM inserted
    `;

    return rows.length > 0;
}

export async function runPodcastDenyBackfill(
    client: BackfillClient,
    apply: boolean,
): Promise<PodcastDenyBackfillResult> {
    if (!apply) {
        const candidates = await listCandidates(client);
        return {
            mode: "dry-run",
            candidateCount: candidates.length,
            deniedPodcastCount: 0,
            candidates,
            denied: [],
        };
    }

    return client.$transaction(async (tx) => {
        const candidates = await listCandidates(tx);
        const denied: CandidateRow[] = [];

        for (const candidate of candidates) {
            if (await applyCandidate(tx, candidate)) {
                denied.push(candidate);
            }
        }

        return {
            mode: "apply",
            candidateCount: candidates.length,
            deniedPodcastCount: denied.length,
            candidates,
            denied,
        };
    });
}

async function configureDatabase(): Promise<PrismaClient> {
    neonConfig.webSocketConstructor = WebSocket;
    const dbModule = await import("../lib/db");
    return dbModule.db;
}

async function main() {
    const apply = hasFlag("--apply");
    const db = await configureDatabase();

    try {
        const result = await runPodcastDenyBackfill(db, apply);
        console.log(
            JSON.stringify(
                {
                    mode: result.mode,
                    candidateCount:
                        result.mode === "dry-run"
                            ? result.candidateCount
                            : undefined,
                    candidateCountBeforeApply:
                        result.mode === "apply"
                            ? result.candidateCount
                            : undefined,
                    deniedPodcastCount:
                        result.mode === "apply"
                            ? result.deniedPodcastCount
                            : undefined,
                    candidates:
                        result.mode === "dry-run"
                            ? result.candidates
                            : undefined,
                    denied: result.mode === "apply" ? result.denied : undefined,
                    nextStep:
                        result.mode === "dry-run"
                            ? "Run bin/deny-podcasts-for-denied-comedians --apply to write podcast_deny_list rows."
                            : undefined,
                },
                null,
                2,
            ),
        );
    } finally {
        await db.$disconnect();
    }
}

if (
    process.argv[1] &&
    path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
    main().catch((error) => {
        console.error(error);
        process.exitCode = 1;
    });
}
