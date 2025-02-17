import { auth } from "@/auth";
import { StatsDataResponse } from "@/app/api/about/interface";
import { APIRoutePath } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";

const AboutPage = async () => {
    const session = await auth();

    const getCachedStats = () =>
        unstable_cache(
            async () => {
                return makeRequest<StatsDataResponse>(APIRoutePath.About);
            },
            ["about-page-data"],
            {
                revalidate: CACHE.stats,
                tags: ["about-page-data"],
            },
        );

    const { stats } = await getCachedStats()();

    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <AboutUsSection />
            <StatsSection
                clubCount={stats.clubCount}
                comedianCount={stats.comedianCount}
                showCount={stats.showCount}
            />
        </main>
    );
};

export default AboutPage;
