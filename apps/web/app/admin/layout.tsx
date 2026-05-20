import { isAdminSession } from "@/lib/auth/requireAdmin";
import {
    BadgeCheck,
    Building2,
    ChevronRight,
    Menu,
    Podcast,
    UserRound,
    UsersRound,
    Workflow,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

const ADMIN_NAV_ITEMS = [
    {
        label: "Users",
        href: "/admin/users",
        description: "Accounts and favorites",
        icon: UserRound,
    },
    {
        label: "Clubs",
        href: "/admin/clubs",
        description: "Club operations",
        icon: Building2,
    },
    {
        label: "Pipelines",
        href: "/admin/pipelines",
        description: "Run status",
        icon: Workflow,
    },
    {
        label: "Comedians",
        href: "/admin/comedians",
        description: "Aliases and blocks",
        icon: UsersRound,
    },
    {
        label: "Podcasts",
        href: "/admin/podcasts/review",
        description: "Ownership review",
        icon: Podcast,
    },
];

export const dynamic = "force-dynamic";

export default async function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    if (!(await isAdminSession())) notFound();

    return (
        <div className="min-h-screen bg-ecru-white text-cedar">
            <header className="border-b border-copper/20 bg-coconut-cream/90">
                <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 md:px-8 lg:flex-row lg:items-center lg:justify-between">
                    <Link
                        href="/admin"
                        className="flex items-center gap-3"
                        aria-label="LaughTrack Admin home"
                    >
                        <Image
                            src="/logomark.svg"
                            alt=""
                            width={42}
                            height={42}
                            className="shrink-0"
                        />
                        <div>
                            <div className="font-gilroy-bold text-h2 leading-tight text-cedar">
                                LaughTrack Admin
                            </div>
                            <div className="font-dmSans text-caption text-soft-charcoal">
                                Operations for live comedy data
                            </div>
                        </div>
                    </Link>
                    <div className="flex flex-wrap items-center gap-3">
                        <details className="group relative">
                            <summary
                                aria-label="Admin navigation"
                                className="flex cursor-pointer list-none items-center gap-2 rounded-md border border-copper/35 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar shadow-sm outline-none hover:bg-copper/10 focus-visible:ring-2 focus-visible:ring-copper/40 [&::-webkit-details-marker]:hidden"
                            >
                                <Menu className="h-5 w-5 text-copper-dark" />
                                Menu
                            </summary>
                            <nav
                                aria-label="Admin navigation"
                                className="absolute right-0 z-30 mt-2 w-72 overflow-hidden rounded-md border border-copper/25 bg-white shadow-xl"
                            >
                                {ADMIN_NAV_ITEMS.map((item) => {
                                    const Icon = item.icon;
                                    return (
                                        <Link
                                            key={item.href}
                                            href={item.href}
                                            className="flex items-center gap-3 border-b border-copper/10 px-4 py-3 text-left last:border-b-0 hover:bg-coconut-cream/60"
                                        >
                                            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-copper/20 bg-coconut-cream text-copper-dark">
                                                <Icon className="h-5 w-5" />
                                            </span>
                                            <span className="min-w-0">
                                                <span className="block font-gilroy-bold text-body leading-tight text-cedar">
                                                    {item.label}
                                                </span>
                                                <span className="block truncate font-dmSans text-caption text-soft-charcoal">
                                                    {item.description}
                                                </span>
                                            </span>
                                        </Link>
                                    );
                                })}
                            </nav>
                        </details>
                        <div className="flex items-center gap-2 rounded-md border border-copper/25 bg-white/70 px-3 py-2 font-dmSans text-caption text-soft-charcoal">
                            <BadgeCheck className="h-4 w-4 text-copper-dark" />
                            Admin access
                        </div>
                    </div>
                </div>
            </header>
            <main
                id="main-content"
                className="mx-auto max-w-7xl px-4 py-8 md:px-8"
            >
                {children}
            </main>
            <footer className="mx-auto flex max-w-7xl items-center gap-2 px-4 pb-8 font-dmSans text-caption text-soft-charcoal md:px-8">
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
