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
import { getDB } from "../database";
import { UserInterface } from "../objects/interfaces";
import ScrapeMenuModal from "../components/custom/modals/ScrapeMenuModal";
const { db } = getDB();

interface RootProps {
    user: UserInterface | null;
    cities: string[];
}

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

async function getRootProps(): Promise<RootProps> {
    const user = getCurrentUser();
    const cities = db.clubs.getAllCities();

    return Promise.all([user, cities]).then((responses) => {
        return {
            user: responses[0],
            cities: responses[1],
        };
    });
}

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const { user, cities } = await getRootProps();

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
                            <ScrapeMenuModal cities={cities} />
                            {children}
                            <Footer />
                        </ClientOnly>
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
