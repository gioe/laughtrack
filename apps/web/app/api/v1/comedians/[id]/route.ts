import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

export async function GET(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const rl = await applyPublicReadRateLimit(req, "comedians-id");
    if (rl instanceof NextResponse) return rl;

    const { id } = await params;
    const numericId = parseInt(id, 10);

    if (isNaN(numericId)) {
        return NextResponse.json(
            { error: "Invalid id" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    try {
        const comedian = await db.comedian.findUnique({
            where: { id: numericId },
            select: {
                id: true,
                uuid: true,
                name: true,
                linktree: true,
                instagramAccount: true,
                instagramFollowers: true,
                tiktokAccount: true,
                tiktokFollowers: true,
                youtubeAccount: true,
                youtubeFollowers: true,
                website: true,
                popularity: true,
                hasImage: true,
            },
        });

        if (!comedian) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        return NextResponse.json(
            {
                data: {
                    id: comedian.id,
                    uuid: comedian.uuid,
                    name: comedian.name,
                    imageUrl: buildComedianImageUrl(
                        comedian.name,
                        comedian.hasImage,
                    ),
                    social_data: {
                        linktree: comedian.linktree,
                        instagram_account: comedian.instagramAccount,
                        instagram_followers: comedian.instagramFollowers,
                        tiktok_account: comedian.tiktokAccount,
                        tiktok_followers: comedian.tiktokFollowers,
                        youtube_account: comedian.youtubeAccount,
                        youtube_followers: comedian.youtubeFollowers,
                        website: comedian.website,
                        popularity: comedian.popularity,
                    },
                },
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/[id] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch comedian" },
            { status: 500 },
        );
    }
}
