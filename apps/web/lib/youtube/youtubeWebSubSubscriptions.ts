const YOUTUBE_WEBSUB_HUB_URL = "https://pubsubhubbub.appspot.com/";
const YOUTUBE_CHANNEL_FEED_URL =
    "https://www.youtube.com/xml/feeds/videos.xml";

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

interface ComedianWithYouTubeChannel {
    uuid: string;
    name: string;
    youtubeChannelId: string | null;
}

interface YouTubeWebSubSubscriptionDbClient {
    comedian: {
        findMany: (args: {
            where: { youtubeChannelId: { not: null } };
            select: {
                uuid: true;
                name: true;
                youtubeChannelId: true;
            };
            orderBy: { id: "asc" };
        }) => Promise<ComedianWithYouTubeChannel[]>;
    };
}

interface YouTubeWebSubSubscriptionLogger {
    warn: (message: string) => void;
}

export interface RenewYouTubeWebSubSubscriptionsOptions {
    dbClient: YouTubeWebSubSubscriptionDbClient;
    fetchFn?: FetchFn;
    callbackUrl: string;
    logger?: YouTubeWebSubSubscriptionLogger;
}

export interface YouTubeWebSubSubscriptionResult {
    comedianId: string;
    comedianName: string;
    youtubeChannelId: string;
    ok: boolean;
    status: number | null;
    error?: string;
}

export interface RenewYouTubeWebSubSubscriptionsResult {
    total: number;
    succeeded: number;
    failed: number;
    results: YouTubeWebSubSubscriptionResult[];
}

export async function renewYouTubeWebSubSubscriptions(
    options: RenewYouTubeWebSubSubscriptionsOptions,
): Promise<RenewYouTubeWebSubSubscriptionsResult> {
    const comedians = await options.dbClient.comedian.findMany({
        where: {
            youtubeChannelId: { not: null },
        },
        select: {
            uuid: true,
            name: true,
            youtubeChannelId: true,
        },
        orderBy: { id: "asc" },
    });

    const results: YouTubeWebSubSubscriptionResult[] = [];

    for (const comedian of comedians) {
        if (!comedian.youtubeChannelId) {
            continue;
        }

        try {
            const response = await (options.fetchFn ?? fetch)(
                YOUTUBE_WEBSUB_HUB_URL,
                {
                    method: "POST",
                    headers: {
                        "content-type": "application/x-www-form-urlencoded",
                    },
                    body: buildSubscribeBody(
                        comedian.youtubeChannelId,
                        options.callbackUrl,
                    ).toString(),
                },
            );

            results.push({
                comedianId: comedian.uuid,
                comedianName: comedian.name,
                youtubeChannelId: comedian.youtubeChannelId,
                ok: response.ok,
                status: response.status,
            });
        } catch (error) {
            const message = getErrorMessage(error);
            options.logger?.warn(
                `[youtube-websub-renewal] failed channel ${comedian.youtubeChannelId} for ${comedian.name}: ${message}`,
            );
            results.push({
                comedianId: comedian.uuid,
                comedianName: comedian.name,
                youtubeChannelId: comedian.youtubeChannelId,
                ok: false,
                status: null,
                error: message,
            });
        }
    }

    return {
        total: results.length,
        succeeded: results.filter((result) => result.ok).length,
        failed: results.filter((result) => !result.ok).length,
        results,
    };
}

function buildSubscribeBody(
    youtubeChannelId: string,
    callbackUrl: string,
): URLSearchParams {
    return new URLSearchParams({
        "hub.mode": "subscribe",
        "hub.topic": buildYouTubeFeedTopicUrl(youtubeChannelId),
        "hub.callback": callbackUrl,
        "hub.verify": "async",
    });
}

function buildYouTubeFeedTopicUrl(youtubeChannelId: string): string {
    const url = new URL(YOUTUBE_CHANNEL_FEED_URL);
    url.searchParams.set("channel_id", youtubeChannelId);
    return url.toString();
}

function getErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message) {
        return error.message;
    }

    return String(error);
}
