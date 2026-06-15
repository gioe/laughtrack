import { neonConfig } from "@neondatabase/serverless";
import { WebSocket } from "ws";
import {
    applyPodcastReviewStateCleanup,
    listPodcastReviewStateCleanupCandidates,
} from "../lib/admin/podcastReviewStateCleanup";

const SCRIPT_ACTOR = "script:standardize-podcast-review-states";

function hasFlag(flag: string): boolean {
    return process.argv.includes(flag);
}

async function main() {
    neonConfig.webSocketConstructor = WebSocket;

    const { db } = await import("../lib/db");
    const apply = hasFlag("--apply");
    const candidates = await listPodcastReviewStateCleanupCandidates(db);

    if (!apply) {
        console.log(
            JSON.stringify(
                {
                    mode: "dry-run",
                    candidateCount: candidates.length,
                    candidates,
                    nextStep:
                        "Run bin/standardize-podcast-review-states --apply to add reviewed no-host podcasts to podcast_deny_list and normalize ignored reviews.",
                },
                null,
                2,
            ),
        );
        await db.$disconnect();
        return;
    }

    const result = await applyPodcastReviewStateCleanup(db, {
        deniedBy: SCRIPT_ACTOR,
    });

    console.log(
        JSON.stringify(
            {
                mode: "apply",
                candidateCountBeforeApply: candidates.length,
                ...result,
            },
            null,
            2,
        ),
    );
    await db.$disconnect();
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
