import "./globals.css";
import "./fonts.css";
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
import { SpeedInsights } from "@vercel/speed-insights/next";
import ToasterProvider from "@/contexts/ToasterProvider";
import LoginModal from "@/ui/components/modals/login";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import { auth } from "@/auth";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

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

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const session = await auth();

    return (
        <SessionProvider>
            <html
                lang="en"
                className={`${bebas.variable} ${oswald.variable} ${inter.variable} ${fjalla.variable} ${chivo.variable} ${dmSams.variable} ${outfit.variable}`}
            >
                <body>
                    <HeroUIProvider>
                        <ScrollPositionManager />
                        <ToasterProvider />
                        <LoginModal />
                        <StyleContextProvider
                            initialContext={StyleContextKey.Home}
                        >
                            {children}
                        </StyleContextProvider>
                        <SpeedInsights />
                    </HeroUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
