import Link from "next/link";
import { auth } from "@/auth";
import { StyleContextProvider } from "@/contexts/StyleProvider";
import { StyleContextKey } from "@/objects/enum";
import Navbar from "@/ui/components/navbar";
import FooterComponent from "@/ui/pages/home/footer";

export default async function NotFound() {
    const session = await auth();

    return (
        <StyleContextProvider initialContext={StyleContextKey.Search}>
            <div className="flex flex-col min-h-screen">
                <Navbar currentUser={session?.profile} />
                <main
                    id="main-content"
                    className="flex-1 flex flex-col items-center justify-center gap-6 bg-coconut-cream px-4 text-center"
                >
                    <p className="text-7xl">🎤</p>
                    <h1 className="text-5xl font-bold text-shark">404</h1>
                    <h2 className="text-2xl font-semibold text-gray-700">
                        This page doesn&apos;t exist
                    </h2>
                    <p className="text-gray-500 max-w-md">
                        The page you&apos;re looking for doesn&apos;t exist or
                        may have moved.
                    </p>
                    <Link href="/" className="btn btn-primary">
                        Go home
                    </Link>
                </main>
                <FooterComponent />
            </div>
        </StyleContextProvider>
    );
}
