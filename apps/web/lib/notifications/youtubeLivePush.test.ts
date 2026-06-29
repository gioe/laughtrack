import { describe, expect, it } from "vitest";

import { buildYouTubeLivePushPayload } from "./youtubeLivePush";

describe("buildYouTubeLivePushPayload", () => {
    it("includes the YouTube live notification type and video identifiers", () => {
        expect(
            buildYouTubeLivePushPayload({
                comedianId: "comedian-uuid",
                comedianName: "Jane Comic",
                youtubeVideoId: "video-123",
                youtubeChannelId: "UC-live-channel",
                videoTitle: "Late set from the club",
                watchUrl: "https://www.youtube.com/watch?v=video-123",
            }),
        ).toEqual({
            title: "Jane Comic is live on YouTube",
            body: "Late set from the club",
            data: {
                type: "youtube_live",
                comedianId: "comedian-uuid",
                youtubeVideoId: "video-123",
                youtubeChannelId: "UC-live-channel",
                watchUrl: "https://www.youtube.com/watch?v=video-123",
            },
        });
    });
});
