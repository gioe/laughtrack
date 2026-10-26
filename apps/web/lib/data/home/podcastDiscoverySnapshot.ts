import { Prisma } from "@prisma/client";
import { db } from "@/lib/db";
import type { PodcastEpisodeDiscoveryDTO } from "./getPodcastEpisodeDiscovery";

export type PublicDiscoveryEpisode = Omit<
    PodcastEpisodeDiscoveryDTO,
    "releaseDate"
> & {
    releaseDate: string;
};

export interface PodcastDiscoverySnapshot {
    generatedAt: string | null;
    episodes: PublicDiscoveryEpisode[];
}

export const EMPTY_PODCAST_SNAPSHOT: PodcastDiscoverySnapshot = {
    generatedAt: null,
    episodes: [],
};

// This is a durable cache read only. Never generate recommendations on a miss.
// No Next data cache: moderation triggers invalidate the database row immediately.
export async function readPodcastDiscoverySnapshot(): Promise<PodcastDiscoverySnapshot> {
    const rows = await db.$queryRaw<
        { payload: PodcastDiscoverySnapshot | null }[]
    >(Prisma.sql`
        SELECT payload FROM podcast_discovery_snapshots
        WHERE id = 1 AND generated_at > NOW() - INTERVAL '24 hours'
    `);
    return rows[0]?.payload ?? EMPTY_PODCAST_SNAPSHOT;
}

export async function refreshPodcastDiscoverySnapshot() {
    // A revision check prevents an in-flight job from republishing a selection
    // invalidated by moderation, or overwriting a newer job's publication.
    const [row] = await db.$queryRaw<{ revision: number }[]>(Prisma.sql`
        SELECT revision FROM podcast_discovery_snapshots WHERE id = 1
    `);
    if (!row)
        throw new Error("Podcast snapshot migration has not been applied");
    const { getPodcastEpisodeDiscovery } = await import(
        "./getPodcastEpisodeDiscovery"
    );
    const episodes = await getPodcastEpisodeDiscovery(null, 5);
    const payload = JSON.stringify({
        generatedAt: new Date().toISOString(),
        episodes,
    });
    const updated = await db.$executeRaw(Prisma.sql`
        UPDATE podcast_discovery_snapshots
        SET payload = ${payload}::jsonb, generated_at = NOW(), revision = revision + 1
        WHERE id = 1 AND revision = ${row.revision}
    `);
    return { published: updated === 1, episodeCount: episodes.length };
}
