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
import { getDB } from "../database";
import { UserInterface } from "../objects/interface";
import Footer from "../components/footer";
import { City } from "../objects/class/city/City";
import { EntityType } from "../objects/enum";
import ScrapeEntitySelectionMenuModal from "../components/modals/scrapeIds";
const { db } = getDB();

interface RootProps {
    user: UserInterface | null;
    cities: City[];
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
    const cities = db.cities.getAll();

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
    const citiesString = JSON.stringify(cities);

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
                            <ScrapeEntitySelectionMenuModal
                                type={EntityType.Club}
                                citiesString={citiesString}
                            />
                            {children}
                            <Footer />
                        </ClientOnly>
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
