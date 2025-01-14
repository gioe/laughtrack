import { auth } from "@/auth";
import { StatsDataResponse, StatsDTO } from "@/app/api/about/interface";
import { APIRoutePath } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import AboutUsSection from "@/ui/pages/about/content";
import StatsSection from "@/ui/pages/about/stats";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";

const AboutPage = async () => {
    const session = await auth();
    const { stats } = await makeRequest<StatsDataResponse>(APIRoutePath.About);
    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />
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
