"use server";

import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

export default async function Page(props: { params: Promise<{ id: string }> }) {
    const session = await auth();
    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>

            <FooterComponent />
        </main>
    );
}
