import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import { CACHE } from "@/util/constants/cacheConstants";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";

const ZIP_RE = /^\d{5}$/;
const HERO_SHOW_COUNT = 3;

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "home");
    if (rl instanceof NextResponse) return rl;

    const zipParam = req.nextUrl.searchParams.get("zip");
    if (zipParam !== null && !ZIP_RE.test(zipParam)) {
        return NextResponse.json(
            { error: "zip must be a 5-digit US zip code" },
            { status: 400 },
        );
    }

    try {
        const session = await auth();
        const sessionZip = session?.profile?.zipCode ?? null;
        // Query ?zip= beats the session profile's stored zip; this lets
        // signed-out callers ask about a location and lets signed-in callers
        // preview a different region without updating their profile.
        const hero = await getHeroContext(zipParam ?? sessionZip);
        const zipCode = hero.zipCode;

        const [
            trendingComedians,
            popularClubs,
            comediansNearYou,
            showsTonight,
            showsNearZip,
            trendingThisWeek,
        ] = await Promise.all([
            getTrendingComedians().catch(() => []),
            getClubs().catch(() => []),
            zipCode
                ? getComediansByZip(zipCode, DEFAULT_HOME_RADIUS_MILES).catch(
                      () => [],
                  )
                : Promise.resolve([]),
            getShowsTonight().catch(() => []),
            zipCode
                ? getShowsNearZip(zipCode, DEFAULT_HOME_RADIUS_MILES).catch(
                      () => [],
                  )
                : Promise.resolve([]),
            getTrendingShowsThisWeek().catch(() => []),
        ]);

        const heroShows = showsNearZip.slice(0, HERO_SHOW_COUNT);
        const moreNearYou = showsNearZip.slice(HERO_SHOW_COUNT);

        return NextResponse.json(
            {
                data: {
                    hero: {
                        zipCode: hero.zipCode,
                        city: hero.city,
                        state: hero.state,
                        shows: heroShows,
                    },
                    trendingComedians,
                    comediansNearYou,
                    showsTonight,
                    moreNearYou,
                    trendingThisWeek,
                    popularClubs,
                },
            },
            {
                headers: {
                    ...rateLimitHeaders(rl),
                    "Cache-Control": `public, s-maxage=${CACHE.home}, stale-while-revalidate=60`,
                },
            },
        );
    } catch (error) {
        console.error("GET /api/v1/home/feed error:", error);
        return NextResponse.json(
            { error: "Failed to fetch home feed" },
            { status: 500 },
        );
    }
}
