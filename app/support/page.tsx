import { auth } from "@/auth";
import { StyleContextKey } from "@/objects/enum";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import SupportSection from "@/ui/pages/support/content";

const SupportPage = async () => {
    const session = await auth();
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <SupportSection />
        </main>
    );
};

export default SupportPage;
