const YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos";

type FetchFn = (input: string, init?: RequestInit) => Promise<Response>;

interface YouTubeVideosListResponse {
    items?: YouTubeVideoListItem[];
}

interface YouTubeVideoListItem {
    id?: string;
    snippet?: {
        channelId?: string;
        title?: string;
        liveBroadcastContent?: "live" | "upcoming" | "none" | string;
    };
    liveStreamingDetails?: {
        actualStartTime?: string;
        actualEndTime?: string;
        scheduledStartTime?: string;
    };
}

export interface VerifyYouTubeLiveStateOptions {
    apiKey: string;
    fetchFn?: FetchFn;
}

export type YouTubeLiveVerification =
    | {
          status: "live";
          videoId: string;
          channelId: string | null;
          title: string | null;
          watchUrl: string;
          actualStartTime: string | null;
          scheduledStartTime: string | null;
      }
    | {
          status: "retry";
          reason: "empty_response" | "missing_live_details" | "upcoming";
          videoId: string;
          channelId: string | null;
          title: string | null;
          scheduledStartTime: string | null;
      }
    | {
          status: "not_live";
          reason: "ended" | "not_broadcast";
          videoId: string;
          channelId: string | null;
          title: string | null;
      };

export async function verifyYouTubeLiveState(
    videoId: string,
    options: VerifyYouTubeLiveStateOptions,
): Promise<YouTubeLiveVerification> {
    const response = await (options.fetchFn ?? fetch)(buildVideosListUrl(videoId, options.apiKey), {
        headers: { accept: "application/json" },
    });

    if (!response.ok) {
        throw new Error(`YouTube videos.list failed with status ${response.status}`);
    }

    const body = (await response.json()) as YouTubeVideosListResponse;
    const item = body.items?.[0];

    if (!item) {
        return retryResult("empty_response", videoId, null, null, null);
    }

    const normalizedVideoId = item.id ?? videoId;
    const channelId = item.snippet?.channelId ?? null;
    const title = item.snippet?.title ?? null;
    const liveStreamingDetails = item.liveStreamingDetails;

    if (!liveStreamingDetails) {
        return retryResult("missing_live_details", normalizedVideoId, channelId, title, null);
    }

    if (liveStreamingDetails.actualEndTime) {
        return {
            status: "not_live",
            reason: "ended",
            videoId: normalizedVideoId,
            channelId,
            title,
        };
    }

    if (item.snippet?.liveBroadcastContent === "live" || liveStreamingDetails.actualStartTime) {
        return {
            status: "live",
            videoId: normalizedVideoId,
            channelId,
            title,
            watchUrl: `https://www.youtube.com/watch?v=${encodeURIComponent(normalizedVideoId)}`,
            actualStartTime: liveStreamingDetails.actualStartTime ?? null,
            scheduledStartTime: liveStreamingDetails.scheduledStartTime ?? null,
        };
    }

    if (item.snippet?.liveBroadcastContent === "upcoming") {
        return retryResult(
            "upcoming",
            normalizedVideoId,
            channelId,
            title,
            liveStreamingDetails.scheduledStartTime ?? null,
        );
    }

    return {
        status: "not_live",
        reason: "not_broadcast",
        videoId: normalizedVideoId,
        channelId,
        title,
    };
}

function buildVideosListUrl(videoId: string, apiKey: string): string {
    const url = new URL(YOUTUBE_VIDEOS_API_URL);
    url.searchParams.set("part", "snippet,liveStreamingDetails");
    url.searchParams.set("id", videoId);
    url.searchParams.set("key", apiKey);

    return url.toString();
}

function retryResult(
    reason: "empty_response" | "missing_live_details" | "upcoming",
    videoId: string,
    channelId: string | null,
    title: string | null,
    scheduledStartTime: string | null,
): YouTubeLiveVerification {
    return {
        status: "retry",
        reason,
        videoId,
        channelId,
        title,
        scheduledStartTime,
    };
}
