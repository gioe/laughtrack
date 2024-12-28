import type { Metadata } from "next";
import "./globals.css";
import ToasterProvider from "../components/providers/toaster";
import LoginModal from "../components/modals/login";
import RegisterModal from "../components/modals/register";
import Header from "../components/header";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import { auth } from "../auth";
import { cache } from "react";
import Footer from "../components/footer";
import { Bebas_Neue, Oswald } from "next/font/google";

const bebas = Bebas_Neue({
    weight: "400",
    subsets: ["latin"],
    display: "swap",
    variable: "--font-bebas",
});

const oswald = Oswald({
    subsets: ["latin"],
    display: "swap",
    variable: "--font-oswald",
});

export const metadata: Metadata = {
    title: "Laughtrack",
    description: "Find funny stuff",
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
            <html lang="en" className={`${bebas.variable} ${oswald.variable}`}>
                <body className="bg-ivory">
                    <NextUIProvider>
                        <Header currentUser={user} />
                        <ToasterProvider />
                        <LoginModal />
                        <RegisterModal />
                        {children}
                        <Footer />
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
