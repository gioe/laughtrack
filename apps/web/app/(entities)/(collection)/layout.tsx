import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import { Suspense } from "react";
import ErrorBoundary from "@/ui/components/errorBoundary";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Navbar currentUser={session?.profile} />
            <ErrorBoundary>
                <Suspense>
                    <main className="flex-1 w-full bg-coconut-cream px-4 sm:px-6 md:px-8">
                        {children}
                    </main>
                </Suspense>
            </ErrorBoundary>
            <FooterComponent />
        </StyleContextProvider>
    );
}
