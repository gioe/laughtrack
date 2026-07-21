import { isAdminSession } from "@/lib/auth/requireAdmin";
import { BadgeCheck, ChevronRight } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import AdminCreateButton from "./AdminCreateButton";
import AdminNavigationMenu from "./AdminNavigationMenu";

export const dynamic = "force-dynamic";

export default async function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    if (!(await isAdminSession())) notFound();

    return (
        <div className="min-h-screen bg-canvas text-foreground">
            <header className="border-b border-copper/20 bg-surface/90">
                <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-5 md:px-8">
                    <AdminNavigationMenu />
                    <Link
                        href="/admin/users"
                        className="flex min-w-0 flex-1 items-center gap-3"
                        aria-label="LaughTrack Admin home"
                    >
                        <Image
                            src="/logomark.svg"
                            alt=""
                            width={42}
                            height={42}
                            className="shrink-0"
                        />
                        <div className="min-w-0">
                            <div className="font-urbanist-bold text-h2 leading-tight text-foreground">
                                LaughTrack Admin
                            </div>
                            <div className="font-dmSans text-caption text-muted-foreground">
                                Operations for live comedy data
                            </div>
                        </div>
                    </Link>
                    <div className="flex shrink-0 items-center gap-2 rounded-md border border-copper/20 bg-surface-elevated/70 px-3 py-2 font-dmSans text-caption text-muted-foreground">
                        <BadgeCheck className="h-4 w-4 text-copper-dark" />
                        Admin access
                    </div>
                </div>
            </header>
            <main
                id="main-content"
                className="mx-auto max-w-7xl px-4 py-8 md:px-8"
            >
                {children}
            </main>
            <AdminCreateButton />
            <footer className="mx-auto flex max-w-7xl items-center gap-2 px-4 pb-8 font-dmSans text-caption text-muted-foreground md:px-8">
                <span>LaughTrack operations</span>
                <ChevronRight className="h-4 w-4 text-copper-dark" />
                <Link
                    href="/"
                    className="font-semibold text-copper-dark hover:underline"
                >
                    Back to public site
                </Link>
            </footer>
        </div>
    );
}
