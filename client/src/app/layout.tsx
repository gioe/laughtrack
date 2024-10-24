import type { Metadata } from "next";
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

export const metadata: Metadata = {
  title: "Laughtrack",
  description: "Find comics you love",
};


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

