import "./globals.css";
import "./fonts.css";
import { ScrollPositionManager } from "@/ui/components/scroll/manager";
import GoogleAdsense from "@/ui/components/google";
import { NextUIProvider } from "@nextui-org/react";
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
import { SpeedInsights } from "@vercel/speed-insights/next";
import { CityProvider } from "@/contexts/CityProvider";
import { getCities } from "@/lib/data/cities/getCities";
import ToasterProvider from "@/contexts/ToasterProvider";
import LoginModal from "@/ui/components/modals/login";
import RegisterModal from "@/ui/components/modals/register";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { unstable_cache } from "next/cache";
import { CACHE } from "@/util/constants/cacheConstants";
import FavoriteRegisterModal from "@/ui/components/modals/favoriteRegister";

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
};

const getCachedCities = unstable_cache(
    async () => {
        return await getCities();
    },
    ["city-data"],
    {
        revalidate: CACHE.home,
        tags: ["city-data"],
    },
);

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const cities = await getCachedCities();

    return (
        <SessionProvider>
            <html
                lang="en"
                className={`${bebas.variable} ${oswald.variable} ${inter.variable} ${fjalla.variable} ${chivo.variable} ${dmSams.variable} ${outfit.variable}`}
            >
                <body>
                    <NextUIProvider>
                        <ScrollPositionManager />
                        <ToasterProvider />
                        <LoginModal />
                        <RegisterModal />
                        <FavoriteRegisterModal />
                        <StyleContextProvider
                            initialContext={StyleContextKey.Home}
                        >
                            <CityProvider initialCities={cities}>
                                {children}
                            </CityProvider>
                        </StyleContextProvider>
                        <SpeedInsights />
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
