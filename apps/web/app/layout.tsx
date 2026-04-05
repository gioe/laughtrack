import "./globals.css";
import "./fonts.css";
import { Suspense } from "react";
import { ScrollPositionManager } from "@/ui/components/scroll/manager";
import { HeroUIProvider } from "@heroui/react";
import { SessionProvider } from "next-auth/react";
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

const SITE_URL = "https://laugh-track.com";
const SITE_TITLE = "LaughTrack — Find Live Comedy Near You";
const SITE_DESCRIPTION =
    "Discover comedy shows, comedians, and tickets near you. Browse upcoming live comedy events, find your favorite comedians, and never miss a show.";
const OG_IMAGE = `${SITE_URL}/logomark-512.png`;

export const metadata: Metadata = {
    title: {
        default: SITE_TITLE,
        template: "%s | LaughTrack",
    },
    description: SITE_DESCRIPTION,
    metadataBase: new URL(SITE_URL),
    alternates: {
        canonical: "/",
    },
    openGraph: {
        title: SITE_TITLE,
        description: SITE_DESCRIPTION,
        url: SITE_URL,
        siteName: "LaughTrack",
        type: "website",
        images: [
            {
                url: OG_IMAGE,
                width: 512,
                height: 512,
                alt: "LaughTrack",
            },
        ],
    },
    twitter: {
        card: "summary",
        title: SITE_TITLE,
        description: SITE_DESCRIPTION,
        images: [OG_IMAGE],
        site: "@laughtrackapp",
    },
    icons: {
        icon: [
            { url: "/logomark-32.png", sizes: "32x32", type: "image/png" },
            { url: "/logomark-64.png", sizes: "64x64", type: "image/png" },
            { url: "/logomark-192.png", sizes: "192x192", type: "image/png" },
            { url: "/logomark-512.png", sizes: "512x512", type: "image/png" },
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
                <body className="flex flex-col min-h-screen">
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
                        </TimezoneProvider>
                    </HeroUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
