import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { Suspense } from "react";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

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
            <Suspense>{children}</Suspense>
            <FooterComponent />
        </StyleContextProvider>
    );
}
