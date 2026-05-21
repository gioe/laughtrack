const PODCAST_ARTWORK_ROUTE = "/api/v1/podcast-artwork";

export function safePodcastImageUrl(url: string | null): string | null {
    const trimmed = url?.trim();
    if (!trimmed) return null;

    let safeUrl: string | null = null;
    if (trimmed.startsWith("//")) {
        safeUrl = `https:${trimmed}`;
    } else if (trimmed.startsWith("https://")) {
        safeUrl = trimmed;
    } else if (trimmed.startsWith("http://")) {
        safeUrl = `https://${trimmed.slice("http://".length)}`;
    }

    if (!safeUrl) return null;
    try {
        const parsed = new URL(safeUrl);
        return parsed.protocol === "https:" ? safeUrl : null;
    } catch {
        return null;
    }
}

export function buildPodcastArtworkUrl(url: string | null): string | null {
    const safeUrl = safePodcastImageUrl(url);
    if (!safeUrl) return null;

    return `${PODCAST_ARTWORK_ROUTE}?url=${encodeURIComponent(safeUrl)}`;
}
