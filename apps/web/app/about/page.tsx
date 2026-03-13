import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import { getStats } from "@/lib/data/stats/getStats";

export const dynamic = "force-dynamic";

const AboutPage = async () => {
    const { clubCount, comedianCount, showCount } = await getStats();

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
