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

export interface UserPushTokenForDelivery {
    id: string;
    platform: string;
    token: string;
}

export interface ApnsYouTubeLiveNotification extends YouTubeLivePushPayload {}

export interface FcmYouTubeLiveMessage {
    notification: {
        title: string;
        body: string;
    };
    data: YouTubeLivePushPayload["data"];
}

export interface PushSendSuccess {
    ok: true;
}

export interface PushSendFailure {
    ok: false;
    status?: number;
    reason?: string;
    errorCode?: string;
}

export type PushSendResult = PushSendSuccess | PushSendFailure;

export interface YouTubeLivePushSenders {
    apns: {
        send: (token: string, notification: ApnsYouTubeLiveNotification) => Promise<PushSendResult>;
    };
    fcm: {
        send: (token: string, message: FcmYouTubeLiveMessage) => Promise<PushSendResult>;
    };
}

export interface SendYouTubeLivePushOptions {
    input: YouTubeLivePushInput;
    tokens: UserPushTokenForDelivery[];
    senders: YouTubeLivePushSenders;
    deactivateToken: (tokenId: string) => Promise<void> | void;
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

export async function sendYouTubeLivePushToTokens(options: SendYouTubeLivePushOptions): Promise<void> {
    const payload = buildYouTubeLivePushPayload(options.input);

    await Promise.all(
        options.tokens.map(async (pushToken) => {
            if (pushToken.platform === "android") {
                const result = await options.senders.fcm.send(pushToken.token, {
                    notification: {
                        title: payload.title,
                        body: payload.body,
                    },
                    data: payload.data,
                });
                if (isInvalidFcmTokenResponse(result)) {
                    await options.deactivateToken(pushToken.id);
                }
                return;
            }

            if (pushToken.platform === "ios") {
                const result = await options.senders.apns.send(pushToken.token, payload);
                if (isInvalidApnsTokenResponse(result)) {
                    await options.deactivateToken(pushToken.id);
                }
            }
        }),
    );
}

export function isInvalidApnsTokenResponse(result: PushSendResult): boolean {
    if (result.ok) {
        return false;
    }

    return (
        (result.status === 410 && result.reason === "Unregistered") ||
        (result.status === 400 &&
            (result.reason === "BadDeviceToken" ||
                result.reason === "DeviceTokenNotForTopic"))
    );
}

export function isInvalidFcmTokenResponse(result: PushSendResult): boolean {
    if (result.ok) {
        return false;
    }

    return (
        result.errorCode === "UNREGISTERED" ||
        result.errorCode === "INVALID_ARGUMENT" ||
        result.errorCode === "messaging/registration-token-not-registered" ||
        result.errorCode === "messaging/invalid-registration-token"
    );
}
