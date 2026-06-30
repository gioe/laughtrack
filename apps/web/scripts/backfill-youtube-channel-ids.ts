import { neonConfig } from "@neondatabase/serverless";
import type { PrismaClient } from "@prisma/client";
import path from "path";
import { fileURLToPath } from "url";
import { WebSocket } from "ws";
import {
    resolveYouTubeChannelId,
    type ResolveYouTubeChannelIdOptions,
} from "../lib/youtube/youtubeChannelResolver";

interface ComedianYouTubeRow {
    id: number;
    uuid: string;
    name: string;
    youtubeAccount: string | null;
    youtubeChannelId: string | null;
}

type BackfillResult =
    | {
          status: "skipped_existing";
          comedian: ComedianSummary;
          existingYoutubeChannelId: string;
      }
    | {
          status: "planned_update" | "updated";
          comedian: ComedianSummary;
          youtubeAccount: string;
          previousYoutubeChannelId: string | null;
          resolvedYoutubeChannelId: string;
          sourceUrl: string | null;
      }
    | {
          status: "no_change";
          comedian: ComedianSummary;
          youtubeAccount: string;
          existingYoutubeChannelId: string;
          sourceUrl: string | null;
      }
    | {
          status: "failed";
          comedian: ComedianSummary;
          youtubeAccount: string;
          reason: string;
          sourceUrl: string | null;
          detail?: string;
      };

interface ComedianSummary {
    id: number;
    uuid: string;
    name: string;
}

interface BackfillOptions extends ResolveYouTubeChannelIdOptions {
    apply: boolean;
    overwrite: boolean;
    limit: number | null;
}

interface BackfillDbClient {
    comedian: {
        findMany: (args: {
            where: {
                youtubeAccount: {
                    not: null;
                };
            };
            select: {
                id: true;
                uuid: true;
                name: true;
                youtubeAccount: true;
                youtubeChannelId: true;
            };
            orderBy: {
                id: "asc";
            };
            take?: number;
        }) => Promise<ComedianYouTubeRow[]>;
        update: (args: {
            where: {
                id: number;
            };
            data: {
                youtubeChannelId: string;
            };
        }) => Promise<unknown>;
    };
}

export async function backfillYouTubeChannelIds(
    db: BackfillDbClient,
    options: BackfillOptions,
): Promise<BackfillResult[]> {
    const comedians = await db.comedian.findMany({
        where: {
            youtubeAccount: {
                not: null,
            },
        },
        select: {
            id: true,
            uuid: true,
            name: true,
            youtubeAccount: true,
            youtubeChannelId: true,
        },
        orderBy: {
            id: "asc",
        },
        ...(options.limit === null ? {} : { take: options.limit }),
    });

    const results: BackfillResult[] = [];

    for (const comedian of comedians) {
        const youtubeAccount = comedian.youtubeAccount?.trim();
        if (!youtubeAccount) {
            continue;
        }

        const existingYoutubeChannelId =
            comedian.youtubeChannelId?.trim() ?? "";
        const comedianSummary = summarizeComedian(comedian);

        if (existingYoutubeChannelId && !options.overwrite) {
            results.push({
                status: "skipped_existing",
                comedian: comedianSummary,
                existingYoutubeChannelId,
            });
            continue;
        }

        const resolution = await resolveYouTubeChannelId(youtubeAccount, {
            fetchFn: options.fetchFn,
        });

        if (resolution.status === "failed") {
            results.push({
                status: "failed",
                comedian: comedianSummary,
                youtubeAccount,
                reason: resolution.reason,
                sourceUrl: resolution.sourceUrl,
                ...(resolution.detail ? { detail: resolution.detail } : {}),
            });
            continue;
        }

        if (existingYoutubeChannelId === resolution.channelId) {
            results.push({
                status: "no_change",
                comedian: comedianSummary,
                youtubeAccount,
                existingYoutubeChannelId,
                sourceUrl: resolution.sourceUrl,
            });
            continue;
        }

        if (options.apply) {
            await db.comedian.update({
                where: {
                    id: comedian.id,
                },
                data: {
                    youtubeChannelId: resolution.channelId,
                },
            });
        }

        results.push({
            status: options.apply ? "updated" : "planned_update",
            comedian: comedianSummary,
            youtubeAccount,
            previousYoutubeChannelId: existingYoutubeChannelId || null,
            resolvedYoutubeChannelId: resolution.channelId,
            sourceUrl: resolution.sourceUrl,
        });
    }

    return results;
}

export function summarizeBackfillResults(
    results: BackfillResult[],
    options: Pick<BackfillOptions, "apply" | "overwrite" | "limit">,
) {
    const summary = {
        mode: options.apply ? "apply" : "dry-run",
        overwrite: options.overwrite,
        limit: options.limit,
        candidateCount: results.length,
        plannedUpdateCount: countByStatus(results, "planned_update"),
        updatedCount: countByStatus(results, "updated"),
        skippedExistingCount: countByStatus(results, "skipped_existing"),
        noChangeCount: countByStatus(results, "no_change"),
        failedCount: countByStatus(results, "failed"),
        results,
    };

    if (options.apply) {
        return summary;
    }

    return {
        ...summary,
        nextStep:
            "Run bin/backfill-youtube-channel-ids --apply to persist planned youtubeChannelId updates.",
    };
}

export function parseArgs(
    argv: string[],
): Pick<BackfillOptions, "apply" | "overwrite" | "limit"> {
    let limit: number | null = null;

    for (let index = 0; index < argv.length; index += 1) {
        const arg = argv[index];
        if (arg === "--limit") {
            const value = argv[index + 1];
            if (!value) {
                throw new Error("--limit requires a positive integer value");
            }
            limit = parseLimit(value);
            index += 1;
            continue;
        }

        if (arg.startsWith("--limit=")) {
            limit = parseLimit(arg.slice("--limit=".length));
        }
    }

    return {
        apply: argv.includes("--apply"),
        overwrite: argv.includes("--overwrite"),
        limit,
    };
}

function parseLimit(value: string): number {
    const limit = Number(value);
    if (!Number.isInteger(limit) || limit < 1) {
        throw new Error("--limit requires a positive integer value");
    }

    return limit;
}

function summarizeComedian(comedian: ComedianYouTubeRow): ComedianSummary {
    return {
        id: comedian.id,
        uuid: comedian.uuid,
        name: comedian.name,
    };
}

function countByStatus(
    results: BackfillResult[],
    status: BackfillResult["status"],
): number {
    return results.filter((result) => result.status === status).length;
}

async function configureDatabase(): Promise<PrismaClient> {
    neonConfig.webSocketConstructor = WebSocket;

    const dbModule = await import("../lib/db");
    return dbModule.db;
}

async function main() {
    let db: PrismaClient | null = null;
    const parsedOptions = parseArgs(process.argv.slice(2));

    try {
        db = await configureDatabase();
        const results = await backfillYouTubeChannelIds(db, parsedOptions);

        console.log(
            JSON.stringify(
                summarizeBackfillResults(results, parsedOptions),
                null,
                2,
            ),
        );
    } finally {
        await db?.$disconnect();
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
