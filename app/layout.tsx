import "./globals.css";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import {
    Bebas_Neue,
    Oswald,
    Inter,
    Fjalla_One,
    DM_Sans,
    Chivo,
} from "next/font/google";
import type { Metadata } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { CityProvider } from "@/contexts/CityProvider";
import { getCities } from "@/lib/data/cities/get";
import ToasterProvider from "@/ui/components/providers/toaster";
import LoginModal from "@/ui/components/modals/login";
import RegisterModal from "@/ui/components/modals/register";

const chivo = Chivo({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-chivo",
});

const dmSams = DM_Sans({
    weight: "400",
    subsets: ["latin"],
    variable: "--font-fjalla",
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

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const cities = await getCities();
    return (
        <SessionProvider>
            <html
                lang="en"
                className={`${bebas.variable} ${oswald.variable} ${inter.variable} ${fjalla.variable} ${dmSams.variable}`}
            >
                <body>
                    <NextUIProvider>
                        <ToasterProvider />
                        <LoginModal />
                        <RegisterModal />
                        <CityProvider initialCities={cities}>
                            {children}
                        </CityProvider>
                        <SpeedInsights />
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
