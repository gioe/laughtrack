import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { db } from "@/lib/db";
import { parseYouTubeWebSubFeed } from "@/lib/youtube/youtubeWebSub";
import { verifyYouTubeLiveState } from "@/lib/youtube/youtubeLiveVerifier";
import {
    sendYouTubeLivePushToTokens,
    type UserPushTokenForDelivery,
    type YouTubeLivePushInput,
    type YouTubeLivePushSenders,
} from "@/lib/notifications/youtubeLivePush";

const YOUTUBE_LIVE_NOTIFICATION_TYPE = "push";

const youtubeLivePushSenders: YouTubeLivePushSenders = {
    apns: {
        send: async () => ({ ok: true }),
    },
    fcm: {
        send: async () => ({ ok: true }),
    },
};

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const challenge = req.nextUrl.searchParams.get("hub.challenge");
    const mode = req.nextUrl.searchParams.get("hub.mode");
    const topic = req.nextUrl.searchParams.get("hub.topic");

    if (!challenge || !mode || !topic) {
        return NextResponse.json({ error: "missing_challenge" }, { status: 400 });
    }

    return new NextResponse(challenge, {
        status: 200,
        headers: { "content-type": "text/plain; charset=utf-8" },
    });
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const xml = await req.text();
    const entries = parseYouTubeWebSubFeed(xml).filter(
        (entry) => entry.videoId && entry.channelId,
    );

    let processed = 0;

    for (const entry of entries) {
        const videoId = entry.videoId as string;
        const channelId = entry.channelId as string;
        const comedian = await findComedianForChannel(channelId);

        if (!comedian) {
            continue;
        }

        const verification = await verifyYouTubeLiveState(videoId, {
            apiKey:
                process.env.YOUTUBE_DATA_API_KEY ??
                process.env.YOUTUBE_API_KEY ??
                "",
        });

        if (verification.status !== "live") {
            continue;
        }

        if (verification.channelId && verification.channelId !== channelId) {
            continue;
        }

        const pushInput: YouTubeLivePushInput = {
            comedianId: comedian.uuid,
            comedianName: comedian.name,
            youtubeVideoId: verification.videoId,
            youtubeChannelId: channelId,
            videoTitle: verification.title ?? entry.title,
            watchUrl: verification.watchUrl,
        };

        for (const favorite of comedian.favoriteComedians) {
            const tokens: UserPushTokenForDelivery[] =
                favorite.user.pushTokens.map((token) => ({
                    id: token.id,
                    platform: token.platform,
                    token: token.token,
                }));

            if (!tokens.length) {
                continue;
            }

            try {
                await db.youTubeLiveNotification.create({
                    data: {
                        userId: favorite.user.userid,
                        comedianId: comedian.uuid,
                        youtubeChannelId: channelId,
                        youtubeVideoId: verification.videoId,
                        videoTitle: pushInput.videoTitle,
                        videoUrl: verification.watchUrl,
                        notificationType: YOUTUBE_LIVE_NOTIFICATION_TYPE,
                    },
                });
            } catch (error) {
                if (isUniqueConstraintError(error)) {
                    continue;
                }
                throw error;
            }

            await sendYouTubeLivePushToTokens({
                input: pushInput,
                tokens,
                senders: youtubeLivePushSenders,
                deactivateToken: deactivatePushToken,
            });
            processed += 1;
        }
    }

    return NextResponse.json({ ok: true, processed }, { status: 202 });
});

function findComedianForChannel(channelId: string) {
    return db.comedian.findFirst({
        where: { youtubeChannelId: channelId },
        select: {
            uuid: true,
            name: true,
            youtubeChannelId: true,
            favoriteComedians: {
                where: {
                    user: {
                        pushShowNotifications: true,
                        pushTokens: { some: { isActive: true } },
                    },
                },
                select: {
                    user: {
                        select: {
                            userid: true,
                            pushTokens: {
                                where: { isActive: true },
                                select: {
                                    id: true,
                                    platform: true,
                                    token: true,
                                },
                            },
                        },
                    },
                },
            },
        },
    });
}

async function deactivatePushToken(tokenId: string): Promise<void> {
    await db.userPushToken.updateMany({
        where: { id: tokenId },
        data: {
            isActive: false,
            revokedAt: new Date(),
        },
    });
}

function isUniqueConstraintError(error: unknown): boolean {
    return (
        typeof error === "object" &&
        error !== null &&
        "code" in error &&
        error.code === "P2002"
    );
}
