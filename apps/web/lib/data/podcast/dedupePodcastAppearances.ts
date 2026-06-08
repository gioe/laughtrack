import { normalizePodcastAppearanceRole } from "@/lib/data/podcast/appearanceRole";

// Minimum field set the dedup needs. The util is generic so each caller's
// richer EpisodeAppearance shape passes through unchanged in the return type.
export type DedupableEpisodeAppearance = {
    id: number;
    appearanceRole: string;
    episode: {
        id: number;
        title: string;
        releaseDate: Date | null;
        podcast: {
            id: number;
        };
    };
};

const APPEARANCE_ROLE_PRIORITY: Record<string, number> = {
    host: 3,
    cohost: 2,
    guest: 1,
};

// Defense-in-depth dedupe for podcast appearances. The primary fix lives at the
// DB layer (uniqueness constraint + backfill on `podcast_episodes`); this
// collapse is a frontend safety net for any future scraper regression that
// slips multiple `podcast_episodes` rows through for one logical episode.
//
// Dedup key: (podcastId, releaseDate.getTime()) when releaseDate is present.
// Same podcast emitting two episodes at the same second is implausible —
// historical dupes always shared the timestamp because they came from the
// same upstream feed entry rescraped under different title-prefix variants.
// Falls back to (podcastId, title) when releaseDate is null so legacy rows
// still collapse.
//
// Tiebreaker: prefer host > cohost > guest, then higher `appearance.id` so the
// most-recently-scraped row wins (likely to carry the freshest audio_url).
// Note this is intentionally distinct from the backfill script's "lowest id
// wins" rule — the two only need to agree when dupes exist, which the DB
// constraint now prevents.
export function dedupePodcastAppearances<T extends DedupableEpisodeAppearance>(
    appearances: T[],
): T[] {
    const byKey = new Map<string, T>();
    for (const appearance of appearances) {
        const podcastId = appearance.episode.podcast.id;
        const releaseStamp = appearance.episode.releaseDate?.getTime();
        const key =
            releaseStamp !== undefined
                ? `${podcastId}|t:${releaseStamp}`
                : `${podcastId}|n:${appearance.episode.title}`;

        const existing = byKey.get(key);
        if (!existing) {
            byKey.set(key, appearance);
            continue;
        }

        const existingPriority =
            APPEARANCE_ROLE_PRIORITY[
                normalizePodcastAppearanceRole(existing.appearanceRole)
            ] ?? 0;
        const candidatePriority =
            APPEARANCE_ROLE_PRIORITY[
                normalizePodcastAppearanceRole(appearance.appearanceRole)
            ] ?? 0;
        if (
            candidatePriority > existingPriority ||
            (candidatePriority === existingPriority &&
                appearance.id > existing.id)
        ) {
            byKey.set(key, appearance);
        }
    }
    return Array.from(byKey.values());
}
