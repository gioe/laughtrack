import { db } from "@/lib/db";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import {
    PUBLIC_SHOW_SELECT,
    mapShowRowToDTO,
} from "@/lib/data/show/showSelect";
import { NO_STORE_CACHE_CONTROL } from "@/lib/httpCache";
import { withRequestMetrics } from "@/lib/metrics";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { NextRequest, NextResponse } from "next/server";

const DEFAULT_PAGE_SIZE = 20;
const MAX_PAGE_SIZE = 50;
const PERIODS = ["upcoming", "past"] as const;

type SavedShowPeriod = (typeof PERIODS)[number];

function parsePositiveInt(value: string | null, fallback: number): number {
    if (!value) return fallback;
    const parsed = Number.parseInt(value, 10);
    return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function parsePeriod(value: string | null): SavedShowPeriod | null {
    if (!value) return "upcoming";
    return PERIODS.find((period) => period === value) ?? null;
}

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
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

        const { searchParams } = new URL(req.url);
        const period = parsePeriod(searchParams.get("period"));
        if (!period) {
            return NextResponse.json(
                { error: "period must be upcoming or past" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }

        const page = parsePositiveInt(searchParams.get("page"), 1);
        const size = Math.min(
            parsePositiveInt(searchParams.get("size"), DEFAULT_PAGE_SIZE),
            MAX_PAGE_SIZE,
        );
        const now = new Date();
        const dateWhere = period === "upcoming" ? { gte: now } : { lt: now };
        const direction = period === "upcoming" ? "asc" : "desc";
        const where = {
            profileId: authCtx.profileId,
            show: {
                date: dateWhere,
                club: { visible: true },
            },
        } as const;

        const [total, savedShows] = await Promise.all([
            db.savedShow.count({ where }),
            db.savedShow.findMany({
                where,
                select: {
                    show: {
                        select: PUBLIC_SHOW_SELECT,
                    },
                },
                orderBy: [{ show: { date: direction } }, { showId: direction }],
                take: size,
                skip: (page - 1) * size,
            }),
        ]);

        const data = savedShows.map(({ show }) =>
            mapShowRowToDTO(show, {
                imageSource: "lineup",
                room: "coalesce",
                distanceWhenNoZip: "undefined",
            }),
        );

        return NextResponse.json(
            {
                data,
                total,
                page,
                size,
                totalPages: Math.max(1, Math.ceil(total / size)),
            },
            {
                headers: {
                    ...rateLimitHeaders(rl),
                    "Cache-Control": NO_STORE_CACHE_CONTROL,
                },
            },
        );
    } catch (error) {
        console.error("GET /api/v1/saved-shows error:", error);
        return NextResponse.json(
            { error: "Failed to fetch saved shows" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
