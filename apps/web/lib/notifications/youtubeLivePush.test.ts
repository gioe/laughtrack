import { describe, expect, it, vi } from "vitest";

import {
    buildYouTubeLivePushPayload,
    sendYouTubeLivePushToTokens,
} from "./youtubeLivePush";

const youtubeLiveInput = {
    comedianId: "comedian-uuid",
    comedianName: "Jane Comic",
    youtubeVideoId: "video-123",
    youtubeChannelId: "UC-live-channel",
    videoTitle: "Late set from the club",
    watchUrl: "https://www.youtube.com/watch?v=video-123",
};

describe("buildYouTubeLivePushPayload", () => {
    it("includes the YouTube live notification type and video identifiers", () => {
        expect(
            buildYouTubeLivePushPayload(youtubeLiveInput),
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

describe("sendYouTubeLivePushToTokens", () => {
    it("delivers equivalent YouTube live data keys to APNs and FCM senders", async () => {
        const apnsSend = vi.fn(async () => ({ ok: true as const }));
        const fcmSend = vi.fn(async () => ({ ok: true as const }));

        await sendYouTubeLivePushToTokens({
            input: youtubeLiveInput,
            tokens: [
                {
                    id: "ios-token-row",
                    platform: "ios",
                    token: "abcdef1234567890",
                },
                {
                    id: "android-token-row",
                    platform: "android",
                    token: "fcm-token",
                },
            ],
            senders: {
                apns: { send: apnsSend },
                fcm: { send: fcmSend },
            },
            deactivateToken: vi.fn(),
        });

        expect(apnsSend).toHaveBeenCalledWith(
            "abcdef1234567890",
            expect.objectContaining({
                title: "Jane Comic is live on YouTube",
                body: "Late set from the club",
                data: {
                    type: "youtube_live",
                    comedianId: "comedian-uuid",
                    youtubeVideoId: "video-123",
                    youtubeChannelId: "UC-live-channel",
                    watchUrl: "https://www.youtube.com/watch?v=video-123",
                },
            }),
        );
        expect(fcmSend).toHaveBeenCalledWith(
            "fcm-token",
            expect.objectContaining({
                notification: {
                    title: "Jane Comic is live on YouTube",
                    body: "Late set from the club",
                },
                data: {
                    type: "youtube_live",
                    comedianId: "comedian-uuid",
                    youtubeVideoId: "video-123",
                    youtubeChannelId: "UC-live-channel",
                    watchUrl: "https://www.youtube.com/watch?v=video-123",
                },
            }),
        );
    });

    it("deactivates APNs and FCM tokens rejected by invalid-token responses", async () => {
        const deactivateToken = vi.fn();

        await sendYouTubeLivePushToTokens({
            input: youtubeLiveInput,
            tokens: [
                {
                    id: "ios-unregistered-row",
                    platform: "ios",
                    token: "apns-unregistered",
                },
                {
                    id: "ios-bad-device-token-row",
                    platform: "ios",
                    token: "apns-bad-device-token",
                },
                {
                    id: "android-unregistered-row",
                    platform: "android",
                    token: "fcm-unregistered",
                },
                {
                    id: "android-invalid-registration-row",
                    platform: "android",
                    token: "fcm-invalid-registration",
                },
            ],
            senders: {
                apns: {
                    send: vi.fn(async (token: string) =>
                        token === "apns-unregistered"
                            ? {
                                  ok: false as const,
                                  status: 410,
                                  reason: "Unregistered",
                              }
                            : {
                                  ok: false as const,
                                  status: 400,
                                  reason: "BadDeviceToken",
                              },
                    ),
                },
                fcm: {
                    send: vi.fn(async (token: string) =>
                        token === "fcm-unregistered"
                            ? {
                                  ok: false as const,
                                  errorCode: "UNREGISTERED",
                              }
                            : {
                                  ok: false as const,
                                  errorCode:
                                      "messaging/invalid-registration-token",
                              },
                    ),
                },
            },
            deactivateToken,
        });

        expect(deactivateToken).toHaveBeenCalledTimes(4);
        expect(deactivateToken).toHaveBeenCalledWith("ios-unregistered-row");
        expect(deactivateToken).toHaveBeenCalledWith("ios-bad-device-token-row");
        expect(deactivateToken).toHaveBeenCalledWith("android-unregistered-row");
        expect(deactivateToken).toHaveBeenCalledWith(
            "android-invalid-registration-row",
        );
    });
});
