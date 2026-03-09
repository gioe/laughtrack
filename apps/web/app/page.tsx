import { auth } from "../auth";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import { getTrendingComedians } from "@/lib/data/home/getTrendingComedians";
import { getClubs } from "@/lib/data/home/getClubs";
import { getComediansByZip } from "@/lib/data/home/getComediansByZip";
import { Prisma } from "@prisma/client";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";
import { ClubDTO } from "@/objects/class/club/club.interface";
import HeroComponent from "@/ui/pages/home/hero";
import TrendingComedianGrid from "@/ui/pages/home/comedians";
import ComedianNearYouSection from "@/ui/pages/home/comedians-near-you";
import TrendingClubsCarousel from "@/ui/pages/home/clubs";
import FooterComponent from "@/ui/pages/home/footer";

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
        return {
            comedians,
            clubs,
        };
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
    const session = await auth();
    const zipCode = session?.profile?.zipCode ?? null;

    const [{ comedians, clubs }, nearYouComedians] = await Promise.all([
        getCachedHomePageData(),
        zipCode
            ? getComediansByZip(zipCode).catch(() => [])
            : Promise.resolve([]),
    ]);

    return (
        <main className="min-h-screen w-full">
            <HeroComponent profile={session?.profile} />
            <TrendingComedianGrid comedians={comedians} />
            {zipCode && nearYouComedians.length > 0 && (
                <ComedianNearYouSection
                    comedians={nearYouComedians}
                    zipCode={zipCode}
                />
            )}
            <TrendingClubsCarousel clubs={clubs} />
            <FooterComponent />
        </main>
    );
}
