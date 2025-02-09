import { auth } from "@/auth";
import { StatsDataResponse } from "@/app/api/about/interface";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import { makeRequest } from "@/util/actions/makeRequest";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import SupportSection from "@/ui/pages/support/content";

const SupportPage = async () => {
    const session = await auth();
    const { stats } = await makeRequest<StatsDataResponse>(APIRoutePath.About);
    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>
            <SupportSection />
            <FooterComponent />
        </main>
    );
};

export default SupportPage;
