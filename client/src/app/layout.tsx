import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";
import ClientOnly from "@/components/custom/ClientOnly";
import ToasterProvider from "@/providers/ToasterProvider";
import LoginModal from "@/components/custom/modals/LoginModal";
import RegisterModal from "@/components/custom/modals/RegisterModal";
import Footer from "@/components/custom/Footer";
import { getCurrentUser } from "@/actions/getCurrentUser";
import { UserInterface } from "@/interfaces/user.interface";
import Header from "@/components/custom/header/Header";

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

