import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const favoriteComedianSelect = {
    id: true,
    uuid: true,
    name: true,
    instagramAccount: true,
    instagramFollowers: true,
    tiktokAccount: true,
    tiktokFollowers: true,
    youtubeAccount: true,
    youtubeFollowers: true,
    website: true,
    popularity: true,
    linktree: true,
    hasImage: true,
    _count: {
        select: {
            lineupItems: true,
        },
    },
} as const;

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorites");
    if (rl instanceof NextResponse) return rl;

    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422, headers: rateLimitHeaders(rl) },
            );
        }
        if (!authCtx) {
            return NextResponse.json(
                { error: "Authentication required" },
                { status: 401, headers: rateLimitHeaders(rl) },
            );
        }

        const favorites = await db.favoriteComedian.findMany({
            where: {
                profileId: authCtx.profileId,
                comedian: { visible: true },
            },
            orderBy: { comedian: { name: "asc" } },
            select: {
                comedian: {
                    select: favoriteComedianSelect,
                },
            },
        });

        return NextResponse.json(
            {
                data: favorites.map(({ comedian }) => ({
                    id: comedian.id,
                    uuid: comedian.uuid,
                    name: comedian.name,
                    imageUrl: buildComedianImageUrl(
                        comedian.name,
                        comedian.hasImage,
                    ),
                    socialData: {
                        id: comedian.id,
                        instagramAccount: comedian.instagramAccount,
                        instagramFollowers: comedian.instagramFollowers,
                        tiktokAccount: comedian.tiktokAccount,
                        tiktokFollowers: comedian.tiktokFollowers,
                        youtubeAccount: comedian.youtubeAccount,
                        youtubeFollowers: comedian.youtubeFollowers,
                        website: comedian.website,
                        popularity: comedian.popularity,
                        linktree: comedian.linktree,
                    },
                    showCount: comedian._count.lineupItems,
                    isFavorite: true,
                })),
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorites" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});

export const POST = withRequestMetrics(async function POST(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorites");
    if (rl instanceof NextResponse) return rl;

    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422, headers: rateLimitHeaders(rl) },
            );
        }
        if (!authCtx) {
            return new NextResponse(null, {
                status: 401,
                headers: rateLimitHeaders(rl),
            });
        }
        const { profileId } = authCtx;

        let body: unknown;
        try {
            body = await req.json();
        } catch {
            return NextResponse.json(
                { error: "Invalid request body" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        const comedianId = (body as Record<string, unknown>)?.comedianId;
        if (!comedianId || typeof comedianId !== "string") {
            return NextResponse.json(
                { error: "comedianId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const comedian = await db.comedian.findUnique({
            where: { uuid: comedianId },
            select: { uuid: true, visible: true },
        });
        if (!comedian || comedian.visible === false) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        await db.favoriteComedian.upsert({
            where: { profileId_comedianId: { profileId, comedianId } },
            create: { profileId, comedianId },
            update: {},
        });

        return NextResponse.json(
            { data: { isFavorited: true } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("POST /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
