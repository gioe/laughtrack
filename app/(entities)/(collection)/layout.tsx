import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";
import { Suspense } from "react";

export default async function EntityDetailLayout({
    children,
}: {
    children: React.ReactNode;
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
