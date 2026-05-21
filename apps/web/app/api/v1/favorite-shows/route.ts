import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { findShowsForHome } from "@/lib/data/home/findShowsForHome";

const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 50;

function parsePositiveInt(value: string | null, fallback: number): number {
    if (!value) return fallback;
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "favorite-shows");
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

        const { searchParams } = new URL(req.url);
        const page = parsePositiveInt(searchParams.get("page"), 1);
        const size = Math.min(
            parsePositiveInt(searchParams.get("size"), DEFAULT_PAGE_SIZE),
            MAX_PAGE_SIZE,
        );

        const where = {
            date: { gte: new Date() },
            club: { visible: true },
            lineupItems: {
                some: {
                    comedian: {
                        favoriteComedians: {
                            some: { profileId: authCtx.profileId },
                        },
                    },
                },
            },
        } as const;

        const [total, data] = await Promise.all([
            db.show.count({ where }),
            findShowsForHome(
                where,
                [{ date: "asc" }, { popularity: "desc" }],
                size,
                {},
                (page - 1) * size,
            ),
        ]);

        return NextResponse.json(
            {
                data,
                total,
                page,
                size,
                totalPages: Math.max(1, Math.ceil(total / size)),
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/favorite-shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch favorite shows" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
