import { NextRequest, NextResponse } from "next/server";
import { getOnboardingComedianSuggestions } from "@/lib/data/comedian/suggestions/getOnboardingComedianSuggestions";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { withRequestMetrics } from "@/lib/metrics";

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "comedians-suggestions");
    if (rl instanceof NextResponse) return rl;

    try {
        // Optional auth: when signed in, populate isFavorite so already-favorited
        // comedians render correctly in the onboarding grid. Anonymous callers
        // (the common onboarding case) skip it.
        const rawAuthCtx = await resolveAuth(req);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;

        const comedians = await getOnboardingComedianSuggestions(
            authCtx?.profileId,
        );

        return NextResponse.json(
            { data: comedians },
            { headers: rateLimitHeaders(rl) },
        );
    } catch (error) {
        console.error("GET /api/v1/comedians/suggestions error:", error);
        return NextResponse.json(
            { error: "Failed to fetch comedian suggestions" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
});
