import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";

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
        {children}
      </body>
    </html>
  );
}

