import type { ReactNode } from "react";
import type { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import type { ClubDTO } from "@/objects/class/club/club.interface";
import type { ShowDTO } from "@/objects/class/show/show.interface";
import type { DiscoveryRailKey } from "@/lib/discovery/railPolicy";
import TrendingClubsCarousel from "./clubs";
import TrendingComedianGrid from "./comedians";
import ShowDiscoverySection from "./shows";

export interface DiscoveryRailPlanEntryData {
    railKey: string;
    payloadKey: string;
    position: number;
    itemIds: readonly (string | number)[];
}

export interface DiscoveryRailPlanData {
    version: number;
    catalogVersion: number;
    policyVersion: number;
    platform: string;
    cycleIndex: number;
    rails: readonly DiscoveryRailPlanEntryData[];
}

export interface DynamicDiscoveryRailItem {
    id?: string | number;
    show: ShowDTO;
    reason: {
        kind: string;
        label: string;
        evidence?: unknown;
    };
}

export interface DynamicDiscoveryRail {
    railKey: string;
    label: string;
    items: readonly DynamicDiscoveryRailItem[];
}

export interface DiscoveryRailPayloads {
    followedComedianShows: readonly ShowDTO[];
    trendingComedians: readonly ComedianDTO[];
    showsTonight: readonly ShowDTO[];
    moreNearYou: readonly ShowDTO[];
    trendingThisWeek: readonly ShowDTO[];
    popularClubs: readonly ClubDTO[];
    dynamicRails: readonly DynamicDiscoveryRail[];
}

export interface DiscoveryRailPlanProps {
    plan: DiscoveryRailPlanData | null | undefined;
    payloads: DiscoveryRailPayloads;
    fallback: ReactNode;
    today: string;
    weekEnd: string;
    zipCode?: string;
    distanceMiles?: number;
    localTrendingComedians?: boolean;
    localPopularClubs?: boolean;
}

type ShowRailPresentation = {
    eyebrow?: string;
    title: string;
    subtitle: string;
    seeAllHref: string;
};

const DYNAMIC_SHOW_RAIL_KEYS = new Set<string>([
    "just_passing_through",
    "rare_returns",
    "only_chance_nearby",
    "newly_added",
    "starting_to_buzz",
    "catch_them_early",
    "from_your_podcasts",
    "because_you_follow_them",
]);

function selectedItems<T>(
    items: readonly T[],
    itemIds: readonly (string | number)[],
    getId: (item: T) => string | number,
): T[] {
    const byId = new Map(items.map((item) => [String(getId(item)), item]));
    return itemIds.flatMap((itemId) => {
        const item = byId.get(String(itemId));
        return item ? [item] : [];
    });
}

function fixedShowPresentation(
    railKey: string,
    props: Pick<
        DiscoveryRailPlanProps,
        "today" | "weekEnd" | "zipCode" | "distanceMiles"
    >,
): ShowRailPresentation | null {
    switch (railKey) {
        case "followed_comedian_shows":
            return {
                eyebrow: "Favorites",
                title: "Your favorites are touring",
                subtitle: "Upcoming shows from comedians you follow",
                seeAllHref: "/show/search",
            };
        case "shows_tonight":
            return {
                title: "Shows tonight",
                subtitle: "Live comedy happening right now, near you",
                seeAllHref: `/show/search?fromDate=${props.today}&toDate=${props.today}`,
            };
        case "nearby_shows":
            return {
                title: "Nearby shows",
                subtitle: "Upcoming shows at clubs in your area",
                seeAllHref: props.zipCode
                    ? `/show/search?zip=${props.zipCode}&distance=${props.distanceMiles ?? 25}`
                    : "/show/search",
            };
        case "trending_this_week":
            return {
                eyebrow: "This week",
                title: "Trending this week",
                subtitle: "The most popular shows happening in the next 7 days",
                seeAllHref: `/show/search?fromDate=${props.today}&toDate=${props.weekEnd}&sort=popularity_desc`,
            };
        default:
            return null;
    }
}

function showRail(
    railKey: DiscoveryRailKey,
    plan: DiscoveryRailPlanData,
    shows: ShowDTO[],
    presentation: ShowRailPresentation,
    reasonLabels?: Record<number, string>,
) {
    if (shows.length === 0) return null;
    return (
        <section
            key={railKey}
            data-discovery-rail-key={railKey}
            className="w-full bg-coconut-cream"
        >
            <ShowDiscoverySection
                {...presentation}
                shows={shows}
                testId={`discovery-rail-${railKey}`}
                reasonLabels={reasonLabels}
                discoveryPresentation={{
                    surface: railKey,
                    policyVersion: String(plan.policyVersion),
                    experimentVariant: "server_directed",
                }}
            />
        </section>
    );
}

function renderRail(
    entry: DiscoveryRailPlanEntryData,
    props: DiscoveryRailPlanProps,
): ReactNode {
    const { payloads, plan } = props;
    if (!plan || !Array.isArray(entry.itemIds)) return null;

    if (entry.railKey === "trending_comedians") {
        if (entry.payloadKey !== "trendingComedians") return null;
        const comedians = selectedItems(
            payloads.trendingComedians,
            entry.itemIds,
            (comedian) => comedian.id,
        );
        if (comedians.length === 0) return null;
        return (
            <section
                key={entry.railKey}
                data-discovery-rail-key={entry.railKey}
                className="w-full bg-coconut-cream"
            >
                <TrendingComedianGrid
                    comedians={comedians}
                    zipCode={
                        props.localTrendingComedians ? props.zipCode : undefined
                    }
                />
            </section>
        );
    }

    if (entry.railKey === "popular_clubs") {
        if (entry.payloadKey !== "popularClubs") return null;
        const clubs = selectedItems(
            payloads.popularClubs,
            entry.itemIds,
            (club) => club.id ?? club.name ?? "",
        );
        if (clubs.length === 0) return null;
        return (
            <section
                key={entry.railKey}
                data-discovery-rail-key={entry.railKey}
                className="w-full bg-coconut-cream"
            >
                <TrendingClubsCarousel
                    clubs={clubs}
                    preserveOrder
                    zipCode={
                        props.localPopularClubs ? props.zipCode : undefined
                    }
                />
            </section>
        );
    }

    const fixedPayloads = {
        followed_comedian_shows: {
            payloadKey: "followedComedianShows",
            items: payloads.followedComedianShows,
        },
        shows_tonight: {
            payloadKey: "showsTonight",
            items: payloads.showsTonight,
        },
        nearby_shows: {
            payloadKey: "moreNearYou",
            items: payloads.moreNearYou,
        },
        trending_this_week: {
            payloadKey: "trendingThisWeek",
            items: payloads.trendingThisWeek,
        },
    } as const;
    const fixed = fixedPayloads[entry.railKey as keyof typeof fixedPayloads];
    if (fixed) {
        if (entry.payloadKey !== fixed.payloadKey) return null;
        const presentation = fixedShowPresentation(entry.railKey, props);
        if (!presentation) return null;
        const shows = selectedItems(
            fixed.items,
            entry.itemIds,
            (show) => show.id,
        );
        return showRail(
            entry.railKey as DiscoveryRailKey,
            plan,
            shows,
            presentation,
        );
    }

    if (!DYNAMIC_SHOW_RAIL_KEYS.has(entry.railKey)) return null;
    if (entry.payloadKey !== "dynamicRails") return null;
    const dynamicRail = payloads.dynamicRails.find(
        (rail) => rail.railKey === entry.railKey,
    );
    if (!dynamicRail) return null;
    const selectedDynamicItems = selectedItems(
        dynamicRail.items,
        entry.itemIds,
        (item) => item.id ?? item.show.id,
    );
    const items =
        entry.railKey === "just_passing_through"
            ? selectedDynamicItems.slice(0, 5)
            : selectedDynamicItems;
    if (items.length === 0) return null;
    const reasons = Object.fromEntries(
        items.map((item) => [item.show.id, item.reason.label]),
    );
    return showRail(
        entry.railKey as DiscoveryRailKey,
        plan,
        items.map((item) => item.show),
        {
            title: dynamicRail.label,
            subtitle: "Recommended from the latest LaughTrack signals",
            seeAllHref: "/show/search",
        },
        reasons,
    );
}

export default function DiscoveryRailPlan(props: DiscoveryRailPlanProps) {
    if (
        !props.plan ||
        !Array.isArray(props.plan.rails) ||
        !props.plan.rails.length
    ) {
        return <>{props.fallback}</>;
    }

    const rails = props.plan.rails.flatMap((entry) => {
        const rendered = renderRail(entry, props);
        return rendered ? [rendered] : [];
    });

    return rails.length > 0 ? <>{rails}</> : <>{props.fallback}</>;
}
