import type { Metadata } from "next";
import "./globals.css";
import ClientOnly from "../components/ClientOnly";
import ToasterProvider from "../components/providers/toaster";
import LoginModal from "../components/modals/login";
import RegisterModal from "../components/modals/register";
import Header from "../components/header";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import { auth } from "../auth";
import { cache } from "react";
import Footer from "../components/footer";
import { EntityType } from "../objects/enum";
import ScrapeEntitySelectionMenuModal from "../components/modals/scrapeIds";
import AddComedianModal from "../components/modals/addComedian";
import { CityProvider } from "../contexts/CityContext";

export const metadata: Metadata = {
    title: "Laughtrack",
    description: "Find comics you love",
};

export const getSession = cache(async () => {
    const session = await auth();
    return session;
});

export async function getCurrentUser() {
    try {
        const session = await getSession();
        if (!session?.user?.email) {
            return null;
        }
        return {
            id: session.user.id,
            email: session.user.email,
            role: session.user.role,
        };
    } catch (error) {
        console.log(error);
        return null;
    }
}

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user = await getCurrentUser();

    return (
        <SessionProvider>
            <html lang="en">
                <body className="bg-shark">
                    <NextUIProvider>
                        <Header currentUser={user} />
                        <CityProvider>
                            <ClientOnly>
                                <ToasterProvider />
                                <LoginModal />
                                <RegisterModal />
                                <ScrapeEntitySelectionMenuModal
                                    type={EntityType.Club}
                                />
                                <AddComedianModal />
                                {children}
                                <Footer />
                            </ClientOnly>
                        </CityProvider>
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
