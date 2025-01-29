import { auth } from "@/auth";
import { StatsDataResponse, StatsDTO } from "@/app/api/about/interface";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";
import { StyleContextProvider } from "@/contexts/StyleProvider";
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
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>{" "}
            <AboutUsSection />
            <StatsSection
                clubCount={stats.clubCount}
                comedianCount={stats.comedianCount}
                showCount={stats.showCount}
            />
            <FooterComponent />
        </main>
    );
};

export default AboutPage;
