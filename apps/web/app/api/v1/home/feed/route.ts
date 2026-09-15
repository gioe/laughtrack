import { NextRequest, NextResponse } from "next/server";
import { withRequestMetrics } from "@/lib/metrics";
import { auth } from "@/auth";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getClubsByZip } from "@/lib/data/home/getClubsByZip";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";
import { getTrendingPodcasts } from "@/lib/data/home/getTrendingPodcasts";
import { getPodcastEpisodeDiscovery } from "@/lib/data/home/getPodcastEpisodeDiscovery";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { getFavoriteComedianShows } from "@/lib/data/home/getFavoriteComedianShows";
import { getDiscoveryRailPolicy } from "@/lib/data/home/getDiscoveryRailPolicy";
import { getTouringScarcityRails } from "@/lib/data/home/getTouringScarcityRails";
import { getFreshAndRisingRails } from "@/lib/data/home/getFreshAndRisingRails";
import { getAffinityRails } from "@/lib/data/home/getAffinityRails";
import {
    DISCOVERY_PLATFORMS,
    type DiscoveryPlatform,
    type DiscoveryRailKey,
} from "@/lib/discovery/railPolicy";
import {
    getDiscoveryRailCycleIndex,
    loadDiscoveryRailPolicyWithFallback,
    selectDiscoveryRailPlan,
    type DiscoveryRailPayloadMap,
} from "@/lib/discovery/railSelector";
import { PROFILE_MISSING, resolveAuth } from "@/lib/auth/resolveAuth";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import { applyPublicReadRateLimit, rateLimitHeaders } from "@/lib/rateLimit";
import { readTimezoneHeader } from "@/util/timezone";

import { inferHeadliner } from "@/util/show/showHeroImage";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import {
    HOME_SHOW_RAIL_CANDIDATE_LIMIT,
    HOME_SHOW_RAIL_LIMIT,
    selectDiverseShowsByTime,
} from "@/lib/data/home/showRailSelection";

function showPayload(payloadKey: string, shows: ShowDTO[]) {
    return {
        payloadKey,
        selectionLimit: HOME_SHOW_RAIL_LIMIT,
        items: shows.map((show) => {
            const performer = inferHeadliner(show);
            return {
                id: show.id,
                performerId: performer?.parentComedian?.id ?? performer?.id,
            };
        }),
    };
}

const ZIP_RE = /^\d{5}$/;
const HERO_SHOW_COUNT = 3;
const MIN_DISTANCE_MILES = 1;
const MAX_DISTANCE_MILES = 100;
// Personalized by session zipCode + Vercel geo-IP, so we opt out of shared
// CDN caching. Short browser cache still absorbs rapid back-button refetches.
const PRIVATE_CACHE_CONTROL = "private, max-age=60";

function logSectionError(section: string) {
    return (error: unknown) => {
        console.error(`home-feed: ${section} failed`, error);
        return [];
    };
}

function logProviderError(section: string) {
    return (error: unknown) => {
        console.error(`home-feed: ${section} failed`, error);
        return null;
    };
}

function isPresent<T>(value: T | null | undefined): value is T {
    return value !== null && value !== undefined;
}

function withDynamicItemIds<
    T extends {
        railKey: DiscoveryRailKey;
        label: string;
        items: readonly { show: { id: number }; performer: { id: number } }[];
    },
>(rail: T) {
    return {
        ...rail,
        items: rail.items.map((item) => ({ ...item, id: item.show.id })),
    };
}

export const GET = withRequestMetrics(async function GET(req: NextRequest) {
    const rl = await applyPublicReadRateLimit(req, "home");
    if (rl instanceof NextResponse) return rl;

    const zipParam = req.nextUrl.searchParams.get("zip");
    const distanceParam = req.nextUrl.searchParams.get("distance");
    const platformParam = req.nextUrl.searchParams.get("platform") ?? "web";
    if (!DISCOVERY_PLATFORMS.includes(platformParam as DiscoveryPlatform)) {
        return NextResponse.json(
            { error: "platform must be one of web, ios, or android" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    const platform = platformParam as DiscoveryPlatform;
    if (zipParam !== null && !ZIP_RE.test(zipParam)) {
        return NextResponse.json(
            { error: "zip must be a 5-digit US zip code" },
            { status: 400, headers: rateLimitHeaders(rl) },
        );
    }
    const distanceMiles =
        distanceParam === null
            ? DEFAULT_HOME_RADIUS_MILES
            : Number(distanceParam);
    if (
        !Number.isFinite(distanceMiles) ||
        !Number.isInteger(distanceMiles) ||
        distanceMiles < MIN_DISTANCE_MILES ||
        distanceMiles > MAX_DISTANCE_MILES
    ) {
        return NextResponse.json(
            { error: "distance must be a number between 1 and 100 miles" },
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
        const [session, rawAuthCtx] = await Promise.all([
            auth(),
            resolveAuth(req),
        ]);
        const authCtx = rawAuthCtx === PROFILE_MISSING ? null : rawAuthCtx;
        const profileId = authCtx?.profileId ?? null;
        const policyPromise = loadDiscoveryRailPolicyWithFallback(
            platform,
            getDiscoveryRailPolicy,
        );
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
            podcastEpisodes,
            trendingPodcasts,
            followedComedianShowCandidates,
            touringScarcityRails,
            freshAndRisingRails,
            affinityRails,
        ] = await Promise.all([
            zipCode
                ? getTrendingComedians(8, 0, {
                      zipCode,
                      distanceMiles,
                  }).catch(logSectionError("getTrendingComedians"))
                : getTrendingComedians().catch(
                      logSectionError("getTrendingComedians"),
                  ),
            // Zip-scope the popular-clubs rail so it re-localizes when the
            // caller changes their zip (iOS already passes ?zip and re-fetches;
            // it was only ever getting the global list back). Fall back to the
            // global list when no zip resolves or no nearby clubs are found.
            zipCode
                ? getClubsByZip(zipCode, distanceMiles, 8, {
                      requireImage: true,
                  })
                      .then((clubs) =>
                          clubs.length > 0
                              ? clubs
                              : getClubs(8, 0, { requireImage: true }),
                      )
                      .catch(logSectionError("getClubsByZip"))
                : getClubs(8, 0, { requireImage: true }).catch(
                      logSectionError("getClubs"),
                  ),
            zipCode
                ? getComediansByZip(zipCode, distanceMiles).catch(
                      logSectionError("getComediansByZip"),
                  )
                : Promise.resolve([]),
            zipCode
                ? getShowsTonight(
                      timezone,
                      zipCode,
                      distanceMiles,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getShowsTonight"))
                : getShowsTonight(
                      timezone,
                      undefined,
                      undefined,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getShowsTonight")),
            zipCode
                ? getShowsNearZip(
                      zipCode,
                      distanceMiles,
                      undefined,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getShowsNearZip"))
                : Promise.resolve([]),
            zipCode
                ? getTrendingShowsThisWeek(
                      timezone,
                      zipCode,
                      distanceMiles,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getTrendingShowsThisWeek"))
                : getTrendingShowsThisWeek(
                      timezone,
                      undefined,
                      undefined,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getTrendingShowsThisWeek")),
            getPodcastEpisodeDiscovery(profileId).catch(
                logSectionError("getPodcastEpisodeDiscovery"),
            ),
            getTrendingPodcasts(zipCode, undefined, distanceMiles).catch(
                logSectionError("getTrendingPodcasts"),
            ),
            profileId
                ? getFavoriteComedianShows(
                      profileId,
                      zipCode,
                      distanceMiles,
                      HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                  ).catch(logSectionError("getFavoriteComedianShows"))
                : Promise.resolve([]),
            getTouringScarcityRails({
                zipCode: zipCode ?? "",
                radiusMiles: distanceMiles,
                limit: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
                forFeedCandidates: true,
            }).catch(logProviderError("getTouringScarcityRails")),
            getFreshAndRisingRails({
                limit: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
            }).catch(logProviderError("getFreshAndRisingRails")),
            getAffinityRails(profileId, {
                limit: HOME_SHOW_RAIL_CANDIDATE_LIMIT,
            }).catch(logProviderError("getAffinityRails")),
        ]);

        const dynamicRails = [
            touringScarcityRails?.justPassingThrough,
            freshAndRisingRails?.startingToBuzz,
            affinityRails?.fromYourPodcasts,
        ]
            .filter(isPresent)
            .map(withDynamicItemIds)
            .filter((rail) => rail.items.length > 0);
        const dynamicPayloads = dynamicRails.reduce<DiscoveryRailPayloadMap>(
            (payloads, rail) => {
                payloads[rail.railKey] = {
                    payloadKey: "dynamicRails",
                    items: rail.items.map((item) => ({
                        id: item.id,
                        performerId: item.performer.id,
                    })),
                    selectionLimit: HOME_SHOW_RAIL_LIMIT,
                };
                return payloads;
            },
            {},
        );

        const heroShows = selectDiverseShowsByTime(showsNearZip).slice(
            0,
            HERO_SHOW_COUNT,
        );
        const heroShowIds = new Set(heroShows.map((show) => show.id));
        const moreNearYou = showsNearZip.filter(
            (show) => !heroShowIds.has(show.id),
        );
        const policy = await policyPromise;
        const railPlan = selectDiscoveryRailPlan({
            policy,
            actorKey: profileId
                ? `profile:${profileId}`
                : `anonymous:${zipCode ?? "global"}`,
            cycleIndex: getDiscoveryRailCycleIndex(
                Date.now(),
                policy.cycleCadenceHours,
            ),
            payloads: {
                shows_tonight: showPayload("showsTonight", showsTonight),
                followed_comedian_shows: showPayload(
                    "followedComedianShows",
                    followedComedianShowCandidates,
                ),
                trending_this_week: showPayload(
                    "trendingThisWeek",
                    trendingThisWeek,
                ),
                trending_comedians: {
                    payloadKey: "trendingComedians",
                    items: trendingComedians,
                },
                popular_clubs: {
                    payloadKey: "popularClubs",
                    items: popularClubs,
                },
                trending_podcasts: {
                    payloadKey: "podcastEpisodes",
                    items: podcastEpisodes,
                },
                nearby_shows: showPayload("moreNearYou", moreNearYou),
                ...dynamicPayloads,
            },
        });

        // Keep legacy payloads bounded and make every plan ID resolvable.
        // Disabled/rotated-out rails retain their normal bounded fallback payload.
        const selectedItems = <T extends { id: number }>(
            key: DiscoveryRailKey,
            items: readonly T[],
        ): T[] => {
            const entry = railPlan.rails.find((rail) => rail.railKey === key);
            if (!entry) return items.slice(0, HOME_SHOW_RAIL_LIMIT);
            const byId = new Map(items.map((item) => [String(item.id), item]));
            return entry.itemIds.flatMap((id) => {
                const item = byId.get(id);
                return item ? [item] : [];
            });
        };

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
                    showsTonight: selectedItems("shows_tonight", showsTonight),
                    moreNearYou: selectedItems("nearby_shows", moreNearYou),
                    trendingThisWeek: selectedItems(
                        "trending_this_week",
                        trendingThisWeek,
                    ),
                    followedComedianShows: selectedItems(
                        "followed_comedian_shows",
                        followedComedianShowCandidates,
                    ),
                    podcastEpisodes,
                    trendingPodcasts,
                    popularClubs,
                    dynamicRails: dynamicRails.map((rail) => ({
                        ...rail,
                        items: selectedItems(rail.railKey, rail.items),
                    })),
                    railPlan,
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
});
