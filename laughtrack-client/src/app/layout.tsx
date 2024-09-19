import type { Metadata } from "next";
import { Nunito } from 'next/font/google'
import "./globals.css";
import ProgressBar from "@badrap/bar-of-progress";
import Router from 'next/router'

const progress = new ProgressBar({
  size: 4,
  color: "#FE595E",
  className: 'z-50',
  delay: 100,
})

Router.events.on('routeChangeStart', progress.start);
Router.events.on('routeChangeComplete', progress.finish);
Router.events.on('routeChangeError', progress.finish);

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

