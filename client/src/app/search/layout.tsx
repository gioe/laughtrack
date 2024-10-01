import { getCurrentUser } from "@/actions/getCurrentUser";
import Footer from "@/components/custom/Footer";
import Header from "@/components/custom/header/Header";


export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const currentUser = await getCurrentUser();

  return (
    <html lang="en">
      <body className="bg-shark">
        <Header
          currentUser={currentUser} />
          {children}
      </body>
    </html>
  );
}
