import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { toggleFavoriteClub } from "@/lib/data/favorites/toggleFavoriteClub";

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ clubId: string }> },
) {
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

        const { clubId: rawClubId } = await params;
        const clubId = Number.parseInt(rawClubId, 10);
        if (!Number.isInteger(clubId) || clubId <= 0) {
            return NextResponse.json(
                { error: "clubId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        // Idempotent: deleteMany via toggleFavoriteClub never throws on 0 rows.
        await toggleFavoriteClub(clubId, profileId, false);

        return NextResponse.json(
            { data: { isFavorited: false } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error(
            "DELETE /api/v1/favorite-clubs/[clubId] error:",
            error,
        );
        return NextResponse.json(
            { error: "Failed to remove favorite club" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
