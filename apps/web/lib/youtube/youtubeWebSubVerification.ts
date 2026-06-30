import { verifyYouTubeLiveState } from "./youtubeLiveVerifier";

type VerifyFn = typeof verifyYouTubeLiveState;

interface YouTubeWebSubEventForVerification {
    id: number;
    youtubeChannelId: string | null;
    youtubeVideoId: string | null;
}

interface YouTubeWebSubVerificationDbClient {
    youTubeWebSubEvent: {
        findMany: (args: {
            where: { eventStatus: "received" };
            select: {
                id: true;
                youtubeChannelId: true;
                youtubeVideoId: true;
            };
            orderBy: { receivedAt: "asc" };
            take: number;
        }) => Promise<YouTubeWebSubEventForVerification[]>;
        findFirst: (args: {
            where: {
                id: { not: number };
                youtubeChannelId: string;
                youtubeVideoId: string;
                verificationStatus: { in: string[] };
            };
            select: { id: true };
        }) => Promise<{ id: number } | null>;
        update: (args: {
            where: { id: number };
            data: Record<string, unknown>;
        }) => Promise<unknown>;
    };
}

export interface VerifyPendingYouTubeWebSubEventsOptions {
    dbClient: YouTubeWebSubVerificationDbClient;
    apiKey: string;
    limit?: number;
    verifyFn?: VerifyFn;
    now?: () => Date;
}

export interface VerifyPendingYouTubeWebSubEventsResult {
    total: number;
    live: number;
    upcoming: number;
    notLive: number;
    duplicate: number;
    failed: number;
    skipped: number;
}

export async function verifyPendingYouTubeWebSubEvents(
    options: VerifyPendingYouTubeWebSubEventsOptions,
): Promise<VerifyPendingYouTubeWebSubEventsResult> {
    const limit = options.limit ?? 50;
    const verifyFn = options.verifyFn ?? verifyYouTubeLiveState;
    const now = options.now ?? (() => new Date());
    const result: VerifyPendingYouTubeWebSubEventsResult = {
        total: 0,
        live: 0,
        upcoming: 0,
        notLive: 0,
        duplicate: 0,
        failed: 0,
        skipped: 0,
    };

    const events = await options.dbClient.youTubeWebSubEvent.findMany({
        where: { eventStatus: "received" },
        select: {
            id: true,
            youtubeChannelId: true,
            youtubeVideoId: true,
        },
        orderBy: { receivedAt: "asc" },
        take: limit,
    });

    result.total = events.length;

    for (const event of events) {
        if (!event.youtubeChannelId || !event.youtubeVideoId) {
            await markFailed(options.dbClient, event.id, {
                failureReason: "missing_channel_or_video",
                verifiedAt: now(),
            });
            result.skipped += 1;
            continue;
        }

        const duplicate = await options.dbClient.youTubeWebSubEvent.findFirst({
            where: {
                id: { not: event.id },
                youtubeChannelId: event.youtubeChannelId,
                youtubeVideoId: event.youtubeVideoId,
                verificationStatus: { in: ["live", "upcoming", "not_live"] },
            },
            select: { id: true },
        });
        if (duplicate) {
            await options.dbClient.youTubeWebSubEvent.update({
                where: { id: event.id },
                data: {
                    eventStatus: "duplicate",
                    verificationStatus: "duplicate",
                    suppressionReason: `duplicate_of:${duplicate.id}`,
                    verifiedAt: now(),
                },
            });
            result.duplicate += 1;
            continue;
        }

        try {
            const verification = await verifyFn(event.youtubeVideoId, {
                apiKey: options.apiKey,
            });

            if (
                verification.channelId &&
                verification.channelId !== event.youtubeChannelId
            ) {
                await markFailed(options.dbClient, event.id, {
                    failureReason: "channel_mismatch",
                    videoTitle: verification.title,
                    verifiedAt: now(),
                });
                result.failed += 1;
                continue;
            }

            if (verification.status === "live") {
                await options.dbClient.youTubeWebSubEvent.update({
                    where: { id: event.id },
                    data: {
                        eventStatus: "verified",
                        verificationStatus: "live",
                        liveBroadcastContent: "live",
                        youtubeVideoId: verification.videoId,
                        youtubeChannelId:
                            verification.channelId ?? event.youtubeChannelId,
                        videoTitle: verification.title,
                        videoUrl: verification.watchUrl,
                        actualStartTime: parseDate(
                            verification.actualStartTime,
                        ),
                        scheduledStartTime: parseDate(
                            verification.scheduledStartTime,
                        ),
                        verifiedAt: now(),
                    },
                });
                result.live += 1;
                continue;
            }

            if (
                verification.status === "retry" &&
                verification.reason === "upcoming"
            ) {
                await options.dbClient.youTubeWebSubEvent.update({
                    where: { id: event.id },
                    data: {
                        eventStatus: "verified",
                        verificationStatus: "upcoming",
                        liveBroadcastContent: "upcoming",
                        youtubeVideoId: verification.videoId,
                        youtubeChannelId:
                            verification.channelId ?? event.youtubeChannelId,
                        videoTitle: verification.title,
                        scheduledStartTime: parseDate(
                            verification.scheduledStartTime,
                        ),
                        verifiedAt: now(),
                    },
                });
                result.upcoming += 1;
                continue;
            }

            if (verification.status === "not_live") {
                await options.dbClient.youTubeWebSubEvent.update({
                    where: { id: event.id },
                    data: {
                        eventStatus: "verified",
                        verificationStatus: "not_live",
                        liveBroadcastContent: "none",
                        youtubeVideoId: verification.videoId,
                        youtubeChannelId:
                            verification.channelId ?? event.youtubeChannelId,
                        videoTitle: verification.title,
                        suppressionReason: verification.reason,
                        verifiedAt: now(),
                    },
                });
                result.notLive += 1;
                continue;
            }

            await markFailed(options.dbClient, event.id, {
                failureReason: verification.reason,
                youtubeVideoId: verification.videoId,
                youtubeChannelId: verification.channelId,
                videoTitle: verification.title,
                verifiedAt: now(),
            });
            result.failed += 1;
        } catch (error) {
            await markFailed(options.dbClient, event.id, {
                failureReason: getErrorMessage(error),
                verifiedAt: now(),
            });
            result.failed += 1;
        }
    }

    return result;
}

function markFailed(
    dbClient: YouTubeWebSubVerificationDbClient,
    eventId: number,
    data: Record<string, unknown>,
): Promise<unknown> {
    return dbClient.youTubeWebSubEvent.update({
        where: { id: eventId },
        data: {
            eventStatus: "failed",
            verificationStatus: "failed",
            ...data,
        },
    });
}

function parseDate(value: string | null): Date | null {
    if (!value) {
        return null;
    }

    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function getErrorMessage(error: unknown): string {
    if (error instanceof Error && error.message) {
        return error.message;
    }

    return String(error);
}
