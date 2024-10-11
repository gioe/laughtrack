import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";
import ClientOnly from "@/components/custom/ClientOnly";
import ToasterProvider from "@/providers/ToasterProvider";
import LoginModal from "@/components/custom/modals/LoginModal";
import RegisterModal from "@/components/custom/modals/RegisterModal";
import Footer from "@/components/custom/Footer";
import { getCurrentUser } from "@/actions/auth/getCurrentUser";
import { UserInterface } from "@/interfaces/user.interface";
import Header from "@/components/custom/header/Header";
import { NextUIProvider } from "@nextui-org/react";
import { SessionProvider } from "next-auth/react";
import AddShowModal from "@/components/custom/modals/AddShowModal";
import AddClubModal from "@/components/custom/modals/AddClubModal";
import AddComedianModal from "@/components/custom/modals/AddComedianModal";
import { use } from "react";

export const metadata: Metadata = {
  title: "Laughtrack",
  description: "Find comics you love",
};

const font = Nunito({
  subsets: ["latin"]
})

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {

  const user = await getCurrentUser() as UserInterface;
  
  return (
    <SessionProvider>
        <html lang="en">
          <body className="bg-shark">
          <NextUIProvider>
            <Header
              currentUser={user}
            />
            <ClientOnly>
              <ToasterProvider />
              <AddShowModal />
              <AddClubModal />
              <AddComedianModal />
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

