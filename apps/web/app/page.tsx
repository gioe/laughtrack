import { auth } from "../auth";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { getShowsTonight } from "@/lib/data/home/getShowsTonight";
import { getShowsNearZip } from "@/lib/data/home/getShowsNearZip";
import { getTrendingShowsThisWeek } from "@/lib/data/home/getTrendingShowsThisWeek";
import { getHeroContext } from "@/lib/data/home/getHeroContext";
import { DEFAULT_HOME_RADIUS_MILES } from "@/util/constants/radiusConstants";
import { Prisma } from "@prisma/client";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import ComedianNearYouSection from "@/ui/pages/home/comedians-near-you";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import ShowDiscoverySection from "@/ui/pages/home/shows";
import FooterComponent from "@/ui/pages/home/footer";
import JsonLd from "@/ui/components/JsonLd";
import { buildWebSiteJsonLd } from "@/util/jsonLd";
import FixtureHomePage from "./page.fixture";

export interface HomePageData {
    comedians: ComedianDTO[];
    clubs: ClubDTO[];
}

async function getHomePageData(): Promise<HomePageData> {
    try {
        const [comedians, clubs] = await Promise.all([
            getTrendingComedians(),
            getClubs(),
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
    if (process.env.E2E_FIXTURE_MODE === "1") {
        return <FixtureHomePage />;
    }

    const session = await auth();
    const heroContext = await getHeroContext(session?.profile?.zipCode ?? null);
    const zipCode = heroContext.zipCode;

    const now = new Date();
    const todayStr = now.toISOString().split("T")[0];
    const weekLater = new Date(now);
    weekLater.setDate(weekLater.getDate() + 6);
    const weekStr = weekLater.toISOString().split("T")[0];

    const [
        { comedians, clubs },
        nearYouComedians,
        showsTonight,
        showsNearYou,
        trendingShowsThisWeek,
    ] = await Promise.all([
        getCachedHomePageData(),
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

    const heroShows = showsNearYou.slice(0, 3);
    const remainingNearYou = showsNearYou.slice(3);

    return (
        <main id="main-content" className="min-h-screen w-full">
            <JsonLd data={buildWebSiteJsonLd()} />
            <HeroComponent
                profile={session?.profile}
                city={heroContext.city}
                state={heroContext.state}
                heroShows={heroShows}
            />
            <section className="w-full bg-white">
                <TrendingComedianGrid comedians={comedians} />
            </section>
            {zipCode && nearYouComedians.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ComedianNearYouSection
                        comedians={nearYouComedians}
                        zipCode={zipCode}
                    />
                </section>
            )}
            {showsTonight.length > 0 && (
                <section className="w-full bg-white">
                    <ShowDiscoverySection
                        title="Shows Tonight"
                        subtitle="Live comedy happening right now, near you"
                        shows={showsTonight}
                        seeAllHref={`/show/search?fromDate=${todayStr}&toDate=${todayStr}`}
                    />
                </section>
            )}
            {zipCode && remainingNearYou.length > 0 && (
                <section className="w-full bg-coconut-cream">
                    <ShowDiscoverySection
                        title="More Near You"
                        subtitle="Upcoming shows at clubs in your area"
                        shows={remainingNearYou}
                        seeAllHref={`/show/search?zip=${zipCode}&distance=${DEFAULT_HOME_RADIUS_MILES}`}
                    />
                </section>
            )}
            {trendingShowsThisWeek.length > 0 && (
                <section className="w-full bg-white">
                    <ShowDiscoverySection
                        title="Trending This Week"
                        subtitle="The most popular shows happening in the next 7 days"
                        shows={trendingShowsThisWeek}
                        seeAllHref={`/show/search?fromDate=${todayStr}&toDate=${weekStr}&sort=popularity_desc`}
                    />
                </section>
            )}
            <section className="w-full bg-white">
                <TrendingClubsCarousel clubs={clubs} />
            </section>
            <FooterComponent />
        </main>
    );
}
