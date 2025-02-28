import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

export default async function AboutPageLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Navbar currentUser={session?.profile} />
            {children}
            <FooterComponent />
        </StyleContextProvider>
    );
}
