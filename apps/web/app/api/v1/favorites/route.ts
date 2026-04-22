import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { buildComedianImageUrl } from "@/util/imageUtil";

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

export async function GET(req: NextRequest) {
    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422 },
            );
        }
        if (!authCtx) {
            return NextResponse.json(
                { error: "Authentication required" },
                { status: 401 },
            );
        }

        const favorites = await db.favoriteComedian.findMany({
            where: { profileId: authCtx.profileId },
            orderBy: { comedian: { name: "asc" } },
            select: {
                comedian: {
                    select: favoriteComedianSelect,
                },
            },
        });

        return NextResponse.json({
            data: favorites.map(({ comedian }) => ({
                id: comedian.id,
                uuid: comedian.uuid,
                name: comedian.name,
                imageUrl: buildComedianImageUrl(
                    comedian.name,
                    comedian.hasImage,
                ),
                social_data: {
                    id: comedian.id,
                    instagram_account: comedian.instagramAccount,
                    instagram_followers: comedian.instagramFollowers,
                    tiktok_account: comedian.tiktokAccount,
                    tiktok_followers: comedian.tiktokFollowers,
                    youtube_account: comedian.youtubeAccount,
                    youtube_followers: comedian.youtubeFollowers,
                    website: comedian.website,
                    popularity: comedian.popularity,
                    linktree: comedian.linktree,
                },
                show_count: comedian._count.lineupItems,
                isFavorite: true,
            })),
        });
    } catch (error) {
        console.error("GET /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorites" },
            { status: 500 },
        );
    }
}

export async function POST(req: NextRequest) {
    try {
        const authCtx = await resolveAuth(req);
        if (authCtx === PROFILE_MISSING) {
            return NextResponse.json(
                {
                    error: "User profile not found. Please sign out and sign in again.",
                },
                { status: 422 },
            );
        }
        if (!authCtx) {
            return new NextResponse(null, { status: 401 });
        }
        const { profileId } = authCtx;

        let body: unknown;
        try {
            body = await req.json();
        } catch {
            return NextResponse.json(
                { error: "Invalid request body" },
                { status: 400 },
            );
        }
        const comedianId = (body as Record<string, unknown>)?.comedianId;
        if (!comedianId || typeof comedianId !== "string") {
            return NextResponse.json(
                { error: "comedianId is required" },
                { status: 400 },
            );
        }

        const comedian = await db.comedian.findUnique({
            where: { uuid: comedianId },
            select: { uuid: true },
        });
        if (!comedian) {
            return NextResponse.json(
                { error: "Comedian not found" },
                { status: 404 },
            );
        }

        await db.favoriteComedian.upsert({
            where: { profileId_comedianId: { profileId, comedianId } },
            create: { profileId, comedianId },
            update: {},
        });

        return NextResponse.json({ data: { isFavorited: true } });
    } catch (error) {
        console.error("POST /api/v1/favorites error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite" },
            { status: 500 },
        );
    }
}
