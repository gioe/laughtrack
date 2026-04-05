import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import { getStats } from "@/lib/data/stats/getStats";
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "About",
    alternates: { canonical: "/about" },
};

export const revalidate = 86400;

const getCachedStats = unstable_cache(
    async () => {
        try {
            return await getStats();
        } catch (error) {
            console.error("About page stats fetch error:", error);
            return { clubCount: 0, comedianCount: 0, showCount: 0 };
        }
    },
    ["about-page-stats"],
    {
        revalidate: CACHE.stats,
        tags: ["about-page-stats"],
    },
);

const AboutPage = async () => {
    const { clubCount, comedianCount, showCount } = await getCachedStats();

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
