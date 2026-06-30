import { db } from "@/lib/db";

/** Global rollout flags (singleton row, id=1). */
export type YouTubeWebSubSettingsView = {
    feedIngestionEnabled: boolean;
    pushDeliveryEnabled: boolean;
};

/** Per-comedian admin row: flags + current subscription + most recent event. */
export type YouTubeWebSubComedianRow = {
    uuid: string;
    name: string;
    youtubeChannelId: string | null;
    youtubeLiveFeedEnabled: boolean;
    youtubeLiveNotificationsEnabled: boolean;
    subscriptionStatus: string | null;
    leaseExpiresAt: string | null;
    lastSubscribeError: string | null;
    recentEventStatus: string | null;
    recentEventAt: string | null;
};

/** Summary row for the event listing table. */
export type YouTubeWebSubEventRow = {
    id: number;
    comedianId: string | null;
    comedianName: string | null;
    youtubeChannelId: string | null;
    youtubeVideoId: string | null;
    videoTitle: string | null;
    eventStatus: string;
    verificationStatus: string | null;
    suppressionReason: string | null;
    failureReason: string | null;
    receivedAt: string;
};

/** Full event detail for the raw-payload viewer. */
export type YouTubeWebSubEventDetail = YouTubeWebSubEventRow & {
    videoUrl: string | null;
    topicUrl: string | null;
    liveBroadcastContent: string | null;
    scheduledStartTime: string | null;
    actualStartTime: string | null;
    publishedAt: string | null;
    verifiedAt: string | null;
    payloadXml: string;
    payloadJson: unknown;
};

export type YouTubeWebSubAdminData = {
    settings: YouTubeWebSubSettingsView;
    comedians: YouTubeWebSubComedianRow[];
    events: YouTubeWebSubEventRow[];
};

const DEFAULT_SETTINGS: YouTubeWebSubSettingsView = {
    feedIngestionEnabled: false,
    pushDeliveryEnabled: false,
};

// Singleton id for youtube_websub_settings (schema default is 1). Read keys off
// the same identity the PATCH handler writes (upsert where id=1).
const SETTINGS_ID = 1;
const COMEDIAN_LIMIT = 250;
const EVENT_LIMIT = 100;

function toIso(value: Date | null | undefined): string | null {
    return value ? value.toISOString() : null;
}

export async function getYouTubeWebSubSettings(): Promise<YouTubeWebSubSettingsView> {
    const setting = await db.youTubeWebSubSetting.findUnique({
        where: { id: SETTINGS_ID },
        select: { feedIngestionEnabled: true, pushDeliveryEnabled: true },
    });
    return setting ?? DEFAULT_SETTINGS;
}

export async function listYouTubeWebSubComedians(
    limit = COMEDIAN_LIMIT,
): Promise<YouTubeWebSubComedianRow[]> {
    const comedians = await db.comedian.findMany({
        where: { youtubeChannelId: { not: null } },
        orderBy: { name: "asc" },
        take: limit,
        select: {
            uuid: true,
            name: true,
            youtubeChannelId: true,
            youtubeLiveFeedEnabled: true,
            youtubeLiveNotificationsEnabled: true,
            youtubeWebSubSubscriptions: {
                select: {
                    status: true,
                    leaseExpiresAt: true,
                    lastSubscribeError: true,
                },
                orderBy: { updatedAt: "desc" },
                take: 1,
            },
            youtubeWebSubEvents: {
                select: { eventStatus: true, receivedAt: true },
                orderBy: { receivedAt: "desc" },
                take: 1,
            },
        },
    });

    return comedians.map((comedian) => {
        const subscription = comedian.youtubeWebSubSubscriptions[0] ?? null;
        const recentEvent = comedian.youtubeWebSubEvents[0] ?? null;
        return {
            uuid: comedian.uuid,
            name: comedian.name,
            youtubeChannelId: comedian.youtubeChannelId,
            youtubeLiveFeedEnabled: comedian.youtubeLiveFeedEnabled,
            youtubeLiveNotificationsEnabled:
                comedian.youtubeLiveNotificationsEnabled,
            subscriptionStatus: subscription?.status ?? null,
            leaseExpiresAt: toIso(subscription?.leaseExpiresAt ?? null),
            lastSubscribeError: subscription?.lastSubscribeError ?? null,
            recentEventStatus: recentEvent?.eventStatus ?? null,
            recentEventAt: toIso(recentEvent?.receivedAt ?? null),
        };
    });
}

export async function listYouTubeWebSubEvents(
    limit = EVENT_LIMIT,
): Promise<YouTubeWebSubEventRow[]> {
    const events = await db.youTubeWebSubEvent.findMany({
        orderBy: { receivedAt: "desc" },
        take: limit,
        select: {
            id: true,
            comedianId: true,
            youtubeChannelId: true,
            youtubeVideoId: true,
            videoTitle: true,
            eventStatus: true,
            verificationStatus: true,
            suppressionReason: true,
            failureReason: true,
            receivedAt: true,
            comedian: { select: { name: true } },
        },
    });

    return events.map((event) => ({
        id: event.id,
        comedianId: event.comedianId,
        comedianName: event.comedian?.name ?? null,
        youtubeChannelId: event.youtubeChannelId,
        youtubeVideoId: event.youtubeVideoId,
        videoTitle: event.videoTitle,
        eventStatus: event.eventStatus,
        verificationStatus: event.verificationStatus,
        suppressionReason: event.suppressionReason,
        failureReason: event.failureReason,
        receivedAt: event.receivedAt.toISOString(),
    }));
}

export async function getYouTubeWebSubEvent(
    id: number,
): Promise<YouTubeWebSubEventDetail | null> {
    const event = await db.youTubeWebSubEvent.findUnique({
        where: { id },
        select: {
            id: true,
            comedianId: true,
            youtubeChannelId: true,
            youtubeVideoId: true,
            videoTitle: true,
            videoUrl: true,
            topicUrl: true,
            eventStatus: true,
            verificationStatus: true,
            liveBroadcastContent: true,
            scheduledStartTime: true,
            actualStartTime: true,
            publishedAt: true,
            verifiedAt: true,
            failureReason: true,
            suppressionReason: true,
            payloadXml: true,
            payloadJson: true,
            receivedAt: true,
            comedian: { select: { name: true } },
        },
    });

    if (!event) return null;

    return {
        id: event.id,
        comedianId: event.comedianId,
        comedianName: event.comedian?.name ?? null,
        youtubeChannelId: event.youtubeChannelId,
        youtubeVideoId: event.youtubeVideoId,
        videoTitle: event.videoTitle,
        videoUrl: event.videoUrl,
        topicUrl: event.topicUrl,
        eventStatus: event.eventStatus,
        verificationStatus: event.verificationStatus,
        liveBroadcastContent: event.liveBroadcastContent,
        scheduledStartTime: toIso(event.scheduledStartTime),
        actualStartTime: toIso(event.actualStartTime),
        publishedAt: toIso(event.publishedAt),
        verifiedAt: toIso(event.verifiedAt),
        suppressionReason: event.suppressionReason,
        failureReason: event.failureReason,
        payloadXml: event.payloadXml,
        payloadJson: event.payloadJson,
        receivedAt: event.receivedAt.toISOString(),
    };
}

export async function getYouTubeWebSubAdminData(): Promise<YouTubeWebSubAdminData> {
    const [settings, comedians, events] = await Promise.all([
        getYouTubeWebSubSettings(),
        listYouTubeWebSubComedians(),
        listYouTubeWebSubEvents(),
    ]);
    return { settings, comedians, events };
}
