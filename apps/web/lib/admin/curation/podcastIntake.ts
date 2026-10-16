import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import { CurationError, type SqlClient } from "./decisions";
export async function lockPodcastIntake(tx: SqlClient): Promise<void> {
    await tx.$queryRaw(Prisma.sql`SELECT curation_lock_intake()`);
}
export async function resolvePodcastIntake(
    tx: SqlClient,
    payload: Record<string, unknown>,
): Promise<number | null> {
    await lockPodcastIntake(tx);
    const json = JSON.stringify(payload);
    const [policy] = await tx.$queryRaw<any[]>(
        Prisma.sql`SELECT * FROM curation_podcast_policy(${json}::jsonb)`,
    );
    if (!policy || ["blocked", "ambiguous"].includes(policy.disposition))
        throw new CurationError(
            "intake_held",
            "Podcast is blocked or has an unresolved identity. Review it in the Review Inbox.",
            422,
        );
    await tx.$queryRaw(
        Prisma.sql`SELECT curation_observe_podcast(${json}::jsonb)`,
    );
    return policy.podcast_id;
}
export async function podcastEpisodesAllowed(id: number): Promise<boolean> {
    const [row] = await db.$queryRaw<{ allowed: boolean }[]>(
        Prisma.sql`SELECT curation_podcast_allowed(${id}) allowed`,
    );
    return row?.allowed === true;
}
