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

// The scraper occasionally writes the same logical podcast episode to multiple
// `podcast_episodes` rows — different RSS feeds re-publishing the same content,
// or one feed adding a numeric prefix to a title that another feed omits. Each
// row gets its own `episode_appearances` join, so a comedian's appearances list
// returns the same episode 2-4× from the API's perspective.
//
// Investigation (2026-06-08): 29,314 dupe groups in podcast_episodes covering
// 29,435 surplus rows. The appearance table itself is unique on
// (episode_id, comedian_id) — the duplication is upstream.
//
// Dedup key: (podcastId, releaseDate.getTime()) when releaseDate is present.
// Same podcast emitting two episodes at the same second is implausible —
// observed dupes always share the timestamp because they come from the same
// upstream feed entry rescraped under different prefix variants. Falls back to
// (podcastId, title) when releaseDate is null so legacy rows still dedupe.
//
// Tiebreaker: prefer host > cohost > guest, then higher `appearance.id` so the
// most-recently-scraped row wins (likely to carry the freshest audio_url).
//
// Used by both the slug-route comedian detail (`findComedianByName`) and the
// v1 numeric-ID route (`/api/v1/comedians/[id]`) so the iOS app — which hits
// the v1 endpoint — sees the same deduped list as the web client.
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
