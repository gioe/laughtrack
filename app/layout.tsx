import "./globals.css";
import ToasterProvider from "../components/providers/toaster";
import LoginModal from "../components/modals/login";
import RegisterModal from "../components/modals/register";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import { auth } from "../auth";
import Footer from "../components/footer";
import {
    Bebas_Neue,
    Oswald,
    Inter,
    Fjalla_One,
    DM_Sans,
    Chivo,
} from "next/font/google";
import Navbar from "../components/navbar";
import type { Metadata } from "next";
import { SpeedInsights } from "@vercel/speed-insights/next";

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
                        {children}
                        <SpeedInsights />
                        <Footer />
                    </NextUIProvider>
                </body>
            </html>
        </SessionProvider>
    );
}
