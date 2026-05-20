const PODCAST_ARTWORK_ROUTE = "/api/v1/podcast-artwork";

export function safePodcastImageUrl(url: string | null): string | null {
    return url?.startsWith("https://") ? url : null;
}

export function buildPodcastArtworkUrl(url: string | null): string | null {
    const safeUrl = safePodcastImageUrl(url);
    if (!safeUrl) return null;

    return `${PODCAST_ARTWORK_ROUTE}?url=${encodeURIComponent(safeUrl)}`;
}
