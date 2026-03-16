import "./globals.css";
import "./fonts.css";
import { Suspense } from "react";
import { ScrollPositionManager } from "@/ui/components/scroll/manager";
import { HeroUIProvider } from "@heroui/react";
import { SessionProvider } from "next-auth/react";
import { Analytics } from "@vercel/analytics/react";
import {
    Bebas_Neue,
    Oswald,
    Inter,
    Fjalla_One,
    DM_Sans,
    Chivo,
    Outfit,
} from "next/font/google";
import type { Metadata } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import ToasterProvider from "@/contexts/ToasterProvider";
import LoginModal from "@/ui/components/modals/login";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";

import { TimezoneProvider } from "@/contexts/TimezoneProvider";
import { ClientTimezone } from "@/contexts/TimezoneCookieProvider";
import ErrorBoundary from "@/ui/components/errorBoundary";

const outfit = Outfit({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-outfit",
});

const chivo = Chivo({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-chivo",
});

const dmSams = DM_Sans({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-dmSans",
});

const fjalla = Fjalla_One({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-fjalla",
});

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
});

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
    icons: {
        icon: [
            { url: "/logomark-32.png", sizes: "32x32", type: "image/png" },
            { url: "/logomark-64.png", sizes: "64x64", type: "image/png" },
            { url: "/logomark-192.png", sizes: "192x192", type: "image/png" },
        ],
        apple: {
            url: "/logomark-192.png",
            sizes: "192x192",
            type: "image/png",
        },
        shortcut: "/logomark.svg",
    },
};

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <SessionProvider>
            <html
                lang="en"
                className={`${bebas.variable} ${oswald.variable} ${inter.variable} ${fjalla.variable} ${chivo.variable} ${dmSams.variable} ${outfit.variable}`}
            >
                <body>
                    <HeroUIProvider>
                        <TimezoneProvider>
                            <ScrollPositionManager />
                            <ToasterProvider />
                            <Suspense fallback={null}>
                                <LoginModal />
                            </Suspense>
                            <StyleContextProvider
                                initialContext={StyleContextKey.Home}
                            >
                                <ClientTimezone />
                                <ErrorBoundary>{children}</ErrorBoundary>
                            </StyleContextProvider>
                            <Analytics />
                            <SpeedInsights />
                        </TimezoneProvider>
                    </HeroUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
