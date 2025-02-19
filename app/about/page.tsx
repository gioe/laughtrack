import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import { getStats } from "@/lib/data/stats/getStats";

const AboutPage = async () => {
    const getCachedStats = () =>
        unstable_cache(
            async () => {
                return await getStats();
            },
            ["about-page-data"],
            {
                revalidate: CACHE.stats,
                tags: ["about-page-data"],
            },
        );

    const { clubCount, comedianCount, showCount } = await getCachedStats()();

    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <AboutUsSection />
            <StatsSection
                clubCount={clubCount}
                comedianCount={comedianCount}
                showCount={showCount}
            />
        </main>
    );
};

export default AboutPage;
