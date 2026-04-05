import SupportSection from "@/ui/pages/support/content";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Support" };

const SupportPage = async () => {
    return (
        <main className="min-h-screen w-full bg-coconut-cream">
            <SupportSection />
        </main>
    );
};

export default SupportPage;
