import { NextRequest, NextResponse } from "next/server";
import { getClubs } from "@/lib/data/home/getClubs";
import {
    applyPublicReadRateLimit,
    parseLimitParam,
    rateLimitHeaders,
} from "@/lib/rateLimit";

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "clubs");
    if (rl instanceof NextResponse) return rl;

    try {
        const limitOrErr = parseLimitParam(req);
        if (limitOrErr instanceof NextResponse) return limitOrErr;
        const limit = limitOrErr;

        const rawOffset = req.nextUrl.searchParams.get("offset");
        const offset = rawOffset !== null ? Number(rawOffset) : 0;
        if (!Number.isInteger(offset) || offset < 0) {
            return NextResponse.json(
                { error: "offset must be a non-negative integer" },
                { status: 400, headers: rateLimitHeaders(rl) },
            );
        }
        const clubs = await getClubs(limit, offset);
        // Map camelCase ClubDTO to snake_case wire shape matching the iOS
        // ClubListItem schema (ios/Sources/LaughTrackAPIClient/openapi.json).
        return NextResponse.json(
            {
                data: clubs.map(({ activeComedianCount, ...rest }) => ({
                    ...rest,
                    active_comedian_count: activeComedianCount,
                })),
            },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/clubs error:", error);
        return NextResponse.json(
            { error: "Failed to fetch clubs" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
