import { getCurrentUser } from "@/actions/getCurrentUser";
import Header from "@/components/header/Header";

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
