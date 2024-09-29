import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";
import ClientOnly from "@/components/ClientOnly";
import ToasterProvider from "@/providers/ToasterProvider";
import LoginModal from "@/components/modals/LoginModal";
import RegisterModal from "@/components/modals/RegisterModal";
import Footer from "@/components/Footer";
import Header from "@/components/header/Header";
import { getCurrentUser } from "@/actions/getCurrentUser";
import { UserInterface } from "@/interfaces/user.interface";

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
    <html lang="en">
      <body className="bg-shark">
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
      </body>
    </html>
  );
}

