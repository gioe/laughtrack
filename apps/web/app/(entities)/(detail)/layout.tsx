import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Suspense } from "react";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import ErrorBoundary from "@/ui/components/errorBoundary";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
    params: Promise<{ name: string }>;
}) {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Navbar currentUser={session?.profile} />
            <Suspense>
                <main className="min-h-screen w-full bg-coconut-cream px-4 sm:px-6 md:px-8">
                    <ErrorBoundary>
                        {children}
                    </ErrorBoundary>
                </main>
            </Suspense>
            <FooterComponent />
        </StyleContextProvider>
    );
}
