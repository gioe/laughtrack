import type { Metadata } from "next";
import "./globals.css";
import ClientOnly from "../components/custom/ClientOnly";
import ToasterProvider from "../components/providers/ToasterProvider";
import LoginModal from "../components/custom/modals/LoginModal";
import RegisterModal from "../components/custom/modals/RegisterModal";
import Footer from "../components/custom/Footer";
import Header from "../components/custom/header/Header";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import { auth } from "../auth";
import { cache } from "react";

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
                        <ClientOnly>
                            <ToasterProvider />
                            <LoginModal />
                            <RegisterModal />
                            {children}
                            <Footer />
                        </ClientOnly>
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
