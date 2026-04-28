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
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";

const ZIP_RE = /^\d{5}$/;
const HERO_SHOW_COUNT = 3;
// Personalized by session zipCode + Vercel geo-IP, so we opt out of shared
// CDN caching. Short browser cache still absorbs rapid back-button refetches.
const PRIVATE_CACHE_CONTROL = "private, max-age=60";

function logSectionError(section: string) {
    return (error: unknown) => {
        console.error(`home-feed: ${section} failed`, error);
        return [];
    };
}

export async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "home");
    if (rl instanceof NextResponse) return rl;

    const zipParam = req.nextUrl.searchParams.get("zip");
    if (zipParam !== null && !ZIP_RE.test(zipParam)) {
        return NextResponse.json(
            { error: "zip must be a 5-digit US zip code" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }

    const tzResult = readTimezoneHeader(req);
    if (!tzResult.ok) {
        return NextResponse.json(
            { error: tzResult.error },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    const timezone = tzResult.timezone;

    try {
        const session = await auth();
        const sessionZip = session?.profile?.zipCode ?? null;
        // Query ?zip= beats the session profile's stored zip; this lets
        // signed-out callers ask about a location and lets signed-in callers
        // preview a different region without updating their profile.
        const hero = await getHeroContext(zipParam ?? sessionZip).catch(
            (error) => {
                console.error("home-feed: getHeroContext failed", error);
                return { zipCode: null, city: null, state: null };
            },
        );
        const zipCode = hero.zipCode;

        const [
            trendingComedians,
            popularClubs,
            comediansNearYou,
            showsTonight,
            showsNearZip,
            trendingThisWeek,
        ] = await Promise.all([
            getTrendingComedians().catch(
                logSectionError("getTrendingComedians"),
            ),
            getClubs(8, 0, { requireImage: true }).catch(
                logSectionError("getClubs"),
            ),
            zipCode
                ? getComediansByZip(zipCode, DEFAULT_HOME_RADIUS_MILES).catch(
                      logSectionError("getComediansByZip"),
                  )
                : Promise.resolve([]),
            getShowsTonight(timezone).catch(logSectionError("getShowsTonight")),
            zipCode
                ? getShowsNearZip(zipCode, DEFAULT_HOME_RADIUS_MILES).catch(
                      logSectionError("getShowsNearZip"),
                  )
                : Promise.resolve([]),
            getTrendingShowsThisWeek(timezone).catch(
                logSectionError("getTrendingShowsThisWeek"),
            ),
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
                    "Cache-Control": PRIVATE_CACHE_CONTROL,
                },
            },
        );
    } catch (error) {
        console.error("GET /api/v1/home/feed error:", error);
        return NextResponse.json(
            { error: "Failed to fetch home feed" },
            { status: 500, headers: rateLimitHeaders(rl) },
        );
    }
}
