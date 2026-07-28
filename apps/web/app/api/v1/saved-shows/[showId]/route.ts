import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { NO_STORE_CACHE_CONTROL } from "@/lib/httpCache";
import { withRequestMetrics } from "@/lib/metrics";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { NextRequest, NextResponse } from "next/server";

type RouteContext = { params: Promise<{ showId: string }> };

function parseShowId(value: string): number | null {
    const showId = Number(value);
    return Number.isSafeInteger(showId) && showId > 0 ? showId : null;
}

function successHeaders(
    rl: Parameters<typeof rateLimitHeaders>[0],
): Record<string, string> {
    return {
        ...rateLimitHeaders(rl),
        "Cache-Control": NO_STORE_CACHE_CONTROL,
    };
}

export const GET = withRequestMetrics(async function GET(
    req: NextRequest,
    { params }: RouteContext,
) {
    const rl = await applyPublicReadRateLimit(req, "saved-shows");
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

        const showId = parseShowId((await params).showId);
        if (!showId) {
            return NextResponse.json(
                { error: "showId must be a positive integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const show = await db.show.findFirst({
            where: { id: showId, club: { visible: true } },
            select: { id: true },
        });
        if (!show) {
            return NextResponse.json(
                { error: "Show not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }

        const savedShow = await db.savedShow.findUnique({
            where: {
                profileId_showId: {
                    profileId: authCtx.profileId,
                    showId,
                },
            },
            select: { showId: true },
        });

        return NextResponse.json(
            { data: { isSaved: Boolean(savedShow) } },
            { headers: successHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/saved-shows/[showId] error:", error);
        return NextResponse.json(
            { error: "Failed to fetch saved-show state" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});

export const POST = withRequestMetrics(async function POST(
    req: NextRequest,
    { params }: RouteContext,
) {
    const rl = await applyPublicReadRateLimit(req, "saved-shows");
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

        const showId = parseShowId((await params).showId);
        if (!showId) {
            return NextResponse.json(
                { error: "showId must be a positive integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const show = await db.show.findFirst({
            where: { id: showId, club: { visible: true } },
            select: { id: true, date: true },
        });
        if (!show) {
            return NextResponse.json(
                { error: "Show not found" },
                { status: 404, headers: rateLimitHeaders(rl) },
            );
        }
        if (show.date < new Date()) {
            return NextResponse.json(
                { error: "Only upcoming shows can be saved" },
                { status: 409, headers: rateLimitHeaders(rl) },
            );
        }

        await db.savedShow.upsert({
            where: {
                profileId_showId: {
                    profileId: authCtx.profileId,
                    showId,
                },
            },
            create: { profileId: authCtx.profileId, showId },
            update: {},
        });

        return NextResponse.json(
            { data: { isSaved: true } },
            { headers: successHeaders(rl) },
        );
    } catch (error) {
        console.error("POST /api/v1/saved-shows/[showId] error:", error);
        return NextResponse.json(
            { error: "Failed to save show" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});

export const DELETE = withRequestMetrics(async function DELETE(
    req: NextRequest,
    { params }: RouteContext,
) {
    const rl = await applyPublicReadRateLimit(req, "saved-shows");
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

        const showId = parseShowId((await params).showId);
        if (!showId) {
            return NextResponse.json(
                { error: "showId must be a positive integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        await db.savedShow.deleteMany({
            where: { profileId: authCtx.profileId, showId },
        });

        return NextResponse.json(
            { data: { isSaved: false } },
            { headers: successHeaders(rl) },
        );
    } catch (error) {
        console.error("DELETE /api/v1/saved-shows/[showId] error:", error);
        return NextResponse.json(
            { error: "Failed to unsave show" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
