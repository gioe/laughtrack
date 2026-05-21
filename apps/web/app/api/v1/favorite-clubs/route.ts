import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { buildClubImageUrl } from "@/util/imageUtil";
import { toggleFavoriteClub } from "@/lib/data/favorites/toggleFavoriteClub";

const favoriteClubSelect = {
    id: true,
    name: true,
    hasImage: true,
} as const;

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorite-clubs");
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

        const favorites = await db.favoriteClub.findMany({
            where: { profileId: authCtx.profileId },
            orderBy: { club: { name: "asc" } },
            select: {
                club: {
                    select: favoriteClubSelect,
                },
            },
        });

        return NextResponse.json(
            {
                data: favorites.map(({ club }) => ({
                    id: club.id,
                    name: club.name,
                    imageUrl: buildClubImageUrl(club.name, club.hasImage),
                    isFavorite: true,
                })),
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/favorite-clubs error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorite clubs" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}

export async function POST(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorite-clubs");
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
        const rawClubId = (body as Record<string, unknown>)?.clubId;
        const clubId =
            typeof rawClubId === "number"
                ? rawClubId
                : typeof rawClubId === "string"
                  ? Number.parseInt(rawClubId, 10)
                  : NaN;
        if (!Number.isInteger(clubId) || clubId <= 0) {
            return NextResponse.json(
                { error: "clubId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const club = await db.club.findUnique({
            where: { id: clubId },
            select: { id: true },
        });
        if (!club) {
            return NextResponse.json(
                { error: "Club not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        await toggleFavoriteClub(clubId, profileId, true);

        return NextResponse.json(
            { data: { isFavorited: true } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("POST /api/v1/favorite-clubs error:", error);
        return NextResponse.json(
            { error: "Failed to add favorite club" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
