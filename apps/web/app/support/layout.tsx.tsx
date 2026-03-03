import { auth } from "@/auth";
import { StyleContextKey } from "@/objects/enum";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

const SupportPageLayout = async ({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) => {
    const session = await auth();
    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <Navbar currentUser={session?.profile} />
            {children}
            <FooterComponent />
        </StyleContextProvider>
    );
};

export default SupportPageLayout;
