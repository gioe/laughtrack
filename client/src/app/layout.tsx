import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";
import ClientOnly from "@/components/ClientOnly";
import ToasterProvider from "@/providers/ToasterProvider";
import LoginModal from "@/components/modals/LoginModal";
import RegisterModal from "@/components/modals/RegisterModal";
import { getCurrentUser } from "@/actions/getCurrentUser";
import Header from "@/components/header/Header";
import Footer from "@/components/Footer";

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

  return (
    <html lang="en">
      <body
        className={font.className}>
        <ClientOnly>
          <ToasterProvider />
          <LoginModal />
          <RegisterModal />
          </ClientOnly>
          {children}
          <Footer />
      </body>
    </html>
  );
}

