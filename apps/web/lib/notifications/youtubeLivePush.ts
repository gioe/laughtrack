export interface YouTubeLivePushInput {
    comedianId: string;
    comedianName: string;
    youtubeVideoId: string;
    youtubeChannelId: string;
    videoTitle: string | null;
    watchUrl: string;
}

export interface YouTubeLivePushPayload {
    title: string;
    body: string;
    data: {
        type: "youtube_live";
        comedianId: string;
        youtubeVideoId: string;
        youtubeChannelId: string;
        watchUrl: string;
    };
}

export function buildYouTubeLivePushPayload(input: YouTubeLivePushInput): YouTubeLivePushPayload {
    return {
        title: `${input.comedianName} is live on YouTube`,
        body: input.videoTitle ?? "Watch now on YouTube",
        data: {
            type: "youtube_live",
            comedianId: input.comedianId,
            youtubeVideoId: input.youtubeVideoId,
            youtubeChannelId: input.youtubeChannelId,
            watchUrl: input.watchUrl,
        },
    };
}
