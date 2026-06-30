const YOUTUBE_ORIGIN = "https://www.youtube.com";
const YOUTUBE_CHANNEL_ID_PATTERN = /^UC[A-Za-z0-9_-]{20,}$/;

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

export type YouTubeChannelResolution =
    | {
          status: "resolved";
          channelId: string;
          sourceUrl: string | null;
      }
    | {
          status: "failed";
          reason: "empty_input" | "fetch_failed" | "not_found" | "ambiguous";
          sourceUrl: string | null;
          detail?: string;
      };

export interface ResolveYouTubeChannelIdOptions {
    fetchFn?: FetchFn;
}

export async function resolveYouTubeChannelId(
    youtubeAccount: string | null | undefined,
    options: ResolveYouTubeChannelIdOptions = {},
): Promise<YouTubeChannelResolution> {
    const lookup = buildYouTubeChannelLookup(youtubeAccount);

    if (lookup.kind === "empty") {
        return {
            status: "failed",
            reason: "empty_input",
            sourceUrl: null,
        };
    }

    if (lookup.kind === "channel_id") {
        return {
            status: "resolved",
            channelId: lookup.channelId,
            sourceUrl: null,
        };
    }

    const sourceUrl = lookup.url;

    try {
        const response = await (options.fetchFn ?? fetch)(sourceUrl, {
            headers: {
                accept: "text/html,application/xhtml+xml",
            },
        });

        if (!response.ok) {
            return {
                status: "failed",
                reason: "fetch_failed",
                sourceUrl,
                detail: `YouTube returned status ${response.status}`,
            };
        }

        return resolveYouTubeChannelIdFromHtml(
            await response.text(),
            sourceUrl,
        );
    } catch (error) {
        return {
            status: "failed",
            reason: "fetch_failed",
            sourceUrl,
            detail: error instanceof Error ? error.message : String(error),
        };
    }
}

export function resolveYouTubeChannelIdFromHtml(
    html: string,
    sourceUrl: string | null,
): YouTubeChannelResolution {
    const canonicalChannelId = extractCanonicalChannelId(html);
    if (canonicalChannelId) {
        return {
            status: "resolved",
            channelId: canonicalChannelId,
            sourceUrl,
        };
    }

    const ids = extractChannelIds(html);
    if (ids.length === 1) {
        return {
            status: "resolved",
            channelId: ids[0],
            sourceUrl,
        };
    }

    if (ids.length > 1) {
        return {
            status: "failed",
            reason: "ambiguous",
            sourceUrl,
            detail: `Found ${ids.length} channel IDs: ${ids.join(", ")}`,
        };
    }

    return {
        status: "failed",
        reason: "not_found",
        sourceUrl,
    };
}

export type YouTubeChannelLookup =
    | { kind: "empty" }
    | { kind: "channel_id"; channelId: string }
    | { kind: "url"; url: string };

export function buildYouTubeChannelLookup(
    youtubeAccount: string | null | undefined,
): YouTubeChannelLookup {
    const normalized = youtubeAccount?.trim();
    if (!normalized) {
        return { kind: "empty" };
    }

    const withoutAt = normalized.startsWith("@")
        ? normalized.slice(1).trim()
        : normalized;
    if (YOUTUBE_CHANNEL_ID_PATTERN.test(withoutAt)) {
        return {
            kind: "channel_id",
            channelId: withoutAt,
        };
    }

    const parsedUrl = parseMaybeUrl(normalized);
    if (parsedUrl) {
        const channelId = extractChannelIdFromPath(parsedUrl.pathname);
        if (channelId) {
            return {
                kind: "channel_id",
                channelId,
            };
        }

        if (isYouTubeHost(parsedUrl.hostname)) {
            return {
                kind: "url",
                url: normalizeYouTubeUrl(parsedUrl),
            };
        }
    }

    return {
        kind: "url",
        url: `${YOUTUBE_ORIGIN}/@${encodeURIComponent(withoutAt.replace(/^\/+/, ""))}`,
    };
}

function parseMaybeUrl(value: string): URL | null {
    try {
        return new URL(value);
    } catch {
        try {
            return new URL(`https://${value}`);
        } catch {
            return null;
        }
    }
}

function normalizeYouTubeUrl(url: URL): string {
    return `${YOUTUBE_ORIGIN}${url.pathname}`;
}

function isYouTubeHost(hostname: string): boolean {
    return (
        /(^|\.)youtube\.com$/i.test(hostname) ||
        /(^|\.)youtu\.be$/i.test(hostname)
    );
}

function extractChannelIdFromPath(pathname: string): string | null {
    const channelPathMatch = pathname.match(/\/channel\/(UC[A-Za-z0-9_-]+)/);
    if (
        channelPathMatch?.[1] &&
        YOUTUBE_CHANNEL_ID_PATTERN.test(channelPathMatch[1])
    ) {
        return channelPathMatch[1];
    }

    return null;
}

function extractCanonicalChannelId(html: string): string | null {
    const canonicalMatch = html.match(
        /<link\s+[^>]*rel=["']canonical["'][^>]*href=["']https:\/\/www\.youtube\.com\/channel\/(UC[A-Za-z0-9_-]+)["'][^>]*>/i,
    );
    if (
        canonicalMatch?.[1] &&
        YOUTUBE_CHANNEL_ID_PATTERN.test(canonicalMatch[1])
    ) {
        return canonicalMatch[1];
    }

    return null;
}

function extractChannelIds(html: string): string[] {
    const ids = new Set<string>();
    const channelIdPattern =
        /"(?:channelId|externalId)"\s*:\s*"(UC[A-Za-z0-9_-]+)"/g;

    for (const match of html.matchAll(channelIdPattern)) {
        const channelId = match[1];
        if (YOUTUBE_CHANNEL_ID_PATTERN.test(channelId)) {
            ids.add(channelId);
        }
    }

    return Array.from(ids).sort();
}
