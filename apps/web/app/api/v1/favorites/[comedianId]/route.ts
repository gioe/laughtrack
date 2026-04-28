import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

export async function DELETE(
    req: NextRequest,
    { params }: { params: Promise<{ comedianId: string }> },
) {
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

        const { comedianId } = await params;
        if (!comedianId) {
            return NextResponse.json(
                { error: "comedianId is required" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        await db.favoriteComedian.delete({
            where: { profileId_comedianId: { profileId, comedianId } },
        });

        return NextResponse.json(
            { data: { isFavorited: false } },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        if (
            error instanceof Prisma.PrismaClientKnownRequestError &&
            error.code === "P2025"
        ) {
            return NextResponse.json(
                { error: "Favorite not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }
        console.error("DELETE /api/v1/favorites/[comedianId] error:", error);
        return NextResponse.json(
            { error: "Failed to remove favorite" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
