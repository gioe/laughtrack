import { auth } from "../auth";
import { cookies } from "next/headers";
import { unstable_cache } from "next/cache";
import { toZonedTime, format } from "date-fns-tz";
import { CACHE } from "@/util/constants/cacheConstants";
import { readTimezoneCookie } from "@/util/timezone";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getClubsByZip } from "@/lib/data/home/getClubsByZip";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZipWithTelemetry } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { getFavoriteComedianShows } from "@/lib/data/home/getFavoriteComedianShows";
import { getDiscoveryRailPolicy } from "@/lib/data/home/getDiscoveryRailPolicy";
import { getTouringScarcityRails } from "@/lib/data/home/getTouringScarcityRails";
import { getFreshAndRisingRails } from "@/lib/data/home/getFreshAndRisingRails";
import { getAffinityRails } from "@/lib/data/home/getAffinityRails";
import {
    isNearYouRankerEnabled,
    resolveNearYouDiscoveryPolicy,
} from "@/lib/data/home/discoveryRanker";
import {
    getDiscoveryRailCycleIndex,
    loadDiscoveryRailPolicyWithFallback,
    selectDiscoveryRailPlan,
    type DiscoveryRailPayloadMap,
} from "@/lib/discovery/railSelector";
import type { DiscoveryRailKey } from "@/lib/discovery/railPolicy";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import { Prisma } from "@prisma/client";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import ShowDiscoverySection from "@/ui/pages/home/shows";
import DiscoveryRailPlan from "@/ui/pages/home/DiscoveryRailPlan";
import FooterComponent from "@/ui/pages/home/footer";
import JsonLd from "@/ui/components/JsonLd";
import { buildWebSiteJsonLd } from "@/util/jsonLd";
import FixtureHomePage from "./page.fixture";

export interface HomePageData {
    comedians: ComedianDTO[];
    clubs: ClubDTO[];
}

function isPresent<T>(value: T | null | undefined): value is T {
    return value !== null && value !== undefined;
}

function withDynamicItemIds<
    T extends {
        railKey: DiscoveryRailKey;
        label: string;
        items: readonly { show: { id: number } }[];
    },
>(rail: T) {
    return {
        ...rail,
        items: rail.items.map((item) => ({ ...item, id: item.show.id })),
    };
}

async function getHomePageData(): Promise<HomePageData> {
    try {
        const [comedians, clubs] = await Promise.all([
            getTrendingComedians(),
            getClubs(8, 0, { requireImage: true }),
        ]);
        return { comedians, clubs };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}

const getCachedHomePageData = unstable_cache(
    async () => {
        try {
            return await getHomePageData();
        } catch (error) {
            console.error("Home page data fetch error:", error);
            throw error;
        }
    },
    ["home-page-data"],
    {
        revalidate: CACHE.home,
        tags: ["home-page-data"],
    },
);

export default async function HomePage() {
    // Belt-and-suspenders: fixture mode is a test-only escape hatch. The
    // VERCEL_ENV guard prevents a stray E2E_FIXTURE_MODE=1 in Vercel
    // production from silently serving fake shows to real users. VERCEL_ENV
    // is only set on Vercel deploys, so CI (where we want fixture mode)
    // stays unaffected.
    if (
        process.env.VERCEL_ENV !== "production" &&
        process.env.E2E_FIXTURE_MODE === "1"
    ) {
        return <FixtureHomePage />;
    }

    const [session, cookieStore] = await Promise.all([auth(), cookies()]);
    const timezone = readTimezoneCookie(cookieStore.get("timezone")?.value);
    const railPolicyPromise = loadDiscoveryRailPolicyWithFallback(
        "web",
        getDiscoveryRailPolicy,
    );
    const heroContext = await getHeroContext(session?.profile?.zipCode ?? null);
    const zipCode = heroContext.zipCode;
    const storedAnonymousVisitorId =
        cookieStore.get("lt_anon_visitor_id")?.value;
    const anonymousVisitorId =
        storedAnonymousVisitorId && storedAnonymousVisitorId.length <= 128
            ? storedAnonymousVisitorId
            : null;
    const discoveryActorKey = session?.profile?.id
        ? `profile:${session.profile.id}`
        : anonymousVisitorId
          ? `anonymous:${anonymousVisitorId}`
          : null;
    const nearYouDiscoveryPolicy = resolveNearYouDiscoveryPolicy({
        enabled: isNearYouRankerEnabled(),
        actorKey: discoveryActorKey,
    });

    // Anchor on the caller's wallclock date (not UTC) so a West Coast user at
    // 10pm PST links to today's calendar date, not UTC tomorrow.
    const nowInTz = toZonedTime(new Date(), timezone);
    const todayStr = format(nowInTz, "yyyy-MM-dd");
    const weekLaterInTz = new Date(nowInTz);
    weekLaterInTz.setDate(weekLaterInTz.getDate() + 6);
    const weekStr = format(weekLaterInTz, "yyyy-MM-dd");

    const [
        { comedians, clubs },
        nearYouComedians,
        nearYouClubs,
        showsTonight,
        nearYouResult,
        trendingShowsThisWeek,
        favoriteComedianShows,
        touringScarcityRails,
        freshAndRisingRails,
        affinityRails,
    ] = await Promise.all([
        getCachedHomePageData(),
        zipCode
            ? getComediansByZip(zipCode, DEFAULT_HOME_RADIUS_MILES, {
                  sortBy: "upcomingShows",
              }).catch(() => [])
            : Promise.resolve([]),
        zipCode
            ? getClubsByZip(zipCode, DEFAULT_HOME_RADIUS_MILES, 8, {
                  requireImage: true,
              }).catch(() => [])
            : Promise.resolve([]),
        zipCode
            ? getShowsTonight(
                  timezone,
                  zipCode,
                  DEFAULT_HOME_RADIUS_MILES,
              ).catch(() => [])
            : getShowsTonight(timezone).catch(() => []),
        zipCode
            ? getShowsNearZipWithTelemetry(zipCode, DEFAULT_HOME_RADIUS_MILES, {
                  actorKey: discoveryActorKey,
                  profileId: session?.profile?.id,
                  experimentVariant: nearYouDiscoveryPolicy.experimentVariant,
              }).catch(() => ({ shows: [], impressionContexts: {} }))
            : Promise.resolve({ shows: [], impressionContexts: {} }),
        getTrendingShowsThisWeek(timezone).catch(() => []),
        session?.profile?.id
            ? getFavoriteComedianShows(session.profile.id).catch(() => [])
            : Promise.resolve([]),
        getTouringScarcityRails({
            zipCode: zipCode ?? "",
            radiusMiles: DEFAULT_HOME_RADIUS_MILES,
        }).catch(() => null),
        getFreshAndRisingRails().catch(() => null),
        getAffinityRails(session?.profile?.id, {
            deduplicateAcrossRails: false,
        }).catch(() => null),
    ]);

    const showsNearYou = nearYouResult.shows;
    const hasLocalShows = showsNearYou.length > 0;
    const heroShows = (
        hasLocalShows ? showsNearYou : trendingShowsThisWeek
    ).slice(0, 6);

    // Single "on the rise" comedian rail: scoped to the viewer's area when we
    // have local results, otherwise the global on-the-rise list.
    const onTheRiseLocal = Boolean(zipCode && nearYouComedians.length > 0);
    const onTheRiseComedians = onTheRiseLocal ? nearYouComedians : comedians;

    // Same treatment for the popular-clubs rail so it re-localizes when the
    // viewer changes their zip; fall back to the global club list otherwise.
    const popularClubsLocal = Boolean(zipCode && nearYouClubs.length > 0);
    const popularClubs = popularClubsLocal ? nearYouClubs : clubs;

    const dynamicRails = [
        touringScarcityRails?.justPassingThrough
            ? withDynamicItemIds(touringScarcityRails.justPassingThrough)
            : null,
        touringScarcityRails?.rareReturns
            ? withDynamicItemIds(touringScarcityRails.rareReturns)
            : null,
        touringScarcityRails?.onlyChanceNearby
            ? withDynamicItemIds(touringScarcityRails.onlyChanceNearby)
            : null,
        freshAndRisingRails?.newlyAdded
            ? withDynamicItemIds(freshAndRisingRails.newlyAdded)
            : null,
        freshAndRisingRails?.startingToBuzz
            ? withDynamicItemIds(freshAndRisingRails.startingToBuzz)
            : null,
        freshAndRisingRails?.catchThemEarly
            ? withDynamicItemIds(freshAndRisingRails.catchThemEarly)
            : null,
        affinityRails?.fromYourPodcasts
            ? withDynamicItemIds(affinityRails.fromYourPodcasts)
            : null,
        affinityRails?.becauseYouFollowThem
            ? withDynamicItemIds(affinityRails.becauseYouFollowThem)
            : null,
    ]
        .filter(isPresent)
        .filter((rail) => rail.items.length > 0);
    const dynamicPayloads = dynamicRails.reduce<DiscoveryRailPayloadMap>(
        (payloads, rail) => {
            payloads[rail.railKey] = {
                payloadKey: "dynamicRails",
                items: rail.items,
            };
            return payloads;
        },
        {},
    );
    const railPolicy = await railPolicyPromise;
    const railPlan = selectDiscoveryRailPlan({
        policy: railPolicy,
        actorKey: discoveryActorKey ?? `anonymous:${zipCode ?? "global"}`,
        cycleIndex: getDiscoveryRailCycleIndex(
            nowInTz,
            railPolicy.cycleCadenceHours,
        ),
        payloads: {
            followed_comedian_shows: {
                payloadKey: "followedComedianShows",
                items: favoriteComedianShows,
            },
            trending_comedians: {
                payloadKey: "trendingComedians",
                items: onTheRiseComedians,
            },
            shows_tonight: {
                payloadKey: "showsTonight",
                items: showsTonight,
            },
            nearby_shows: {
                payloadKey: "moreNearYou",
                items: showsNearYou,
            },
            trending_this_week: {
                payloadKey: "trendingThisWeek",
                items: trendingShowsThisWeek,
            },
            popular_clubs: {
                payloadKey: "popularClubs",
                items: popularClubs,
            },
            ...dynamicPayloads,
        },
    });

    const fallbackRails = (
        <>
            {favoriteComedianShows.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ShowDiscoverySection
                        eyebrow="Favorites"
                        title="Your favorites are touring"
                        subtitle="Upcoming shows from comedians you follow"
                        shows={favoriteComedianShows}
                        seeAllHref="/show/search"
                        testId="favorite-comedian-shows"
                    />
                </section>
            )}
            <section className="w-full bg-coconut-cream">
                <TrendingComedianGrid
                    comedians={onTheRiseComedians}
                    zipCode={onTheRiseLocal && zipCode ? zipCode : undefined}
                />
            </section>
            {showsTonight.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ShowDiscoverySection
                        title="Shows tonight"
                        subtitle="Live comedy happening right now, near you"
                        shows={showsTonight}
                        seeAllHref={`/show/search?fromDate=${todayStr}&toDate=${todayStr}`}
                    />
                </section>
            )}
            {zipCode && showsNearYou.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ShowDiscoverySection
                        title="Nearby shows"
                        subtitle="Upcoming shows at clubs in your area"
                        shows={showsNearYou}
                        seeAllHref={`/show/search?zip=${zipCode}&distance=${DEFAULT_HOME_RADIUS_MILES}`}
                        discoveryPresentation={{
                            surface: "near_you",
                            policyVersion: nearYouDiscoveryPolicy.policyVersion,
                            experimentVariant:
                                nearYouDiscoveryPolicy.experimentVariant,
                            showContexts: nearYouResult.impressionContexts,
                        }}
                    />
                </section>
            )}
            {trendingShowsThisWeek.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ShowDiscoverySection
                        eyebrow="This week"
                        title="Trending this week"
                        subtitle="The most popular shows happening in the next 7 days"
                        shows={trendingShowsThisWeek}
                        seeAllHref={`/show/search?fromDate=${todayStr}&toDate=${weekStr}&sort=popularity_desc`}
                    />
                </section>
            )}
            <section className="w-full bg-coconut-cream">
                <TrendingClubsCarousel
                    clubs={popularClubs}
                    zipCode={popularClubsLocal && zipCode ? zipCode : undefined}
                />
            </section>
        </>
    );

    return (
        <main id="main-content" className="min-h-screen w-full">
            <JsonLd data={buildWebSiteJsonLd()} />
            <HeroComponent
                profile={session?.profile}
                city={heroContext.city}
                state={heroContext.state}
                heroShows={heroShows}
                hasLocalShows={hasLocalShows}
            />
            <DiscoveryRailPlan
                plan={railPlan}
                payloads={{
                    followedComedianShows: favoriteComedianShows,
                    trendingComedians: onTheRiseComedians,
                    showsTonight,
                    moreNearYou: showsNearYou,
                    trendingThisWeek: trendingShowsThisWeek,
                    popularClubs,
                    dynamicRails,
                }}
                fallback={fallbackRails}
                today={todayStr}
                weekEnd={weekStr}
                zipCode={zipCode ?? undefined}
                distanceMiles={DEFAULT_HOME_RADIUS_MILES}
                localTrendingComedians={onTheRiseLocal}
                localPopularClubs={popularClubsLocal}
            />
            <FooterComponent />
        </main>
    );
}
