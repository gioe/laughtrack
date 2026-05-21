"use client";

import {
    Building2,
    Menu,
    Podcast,
    UserRound,
    UsersRound,
    Workflow,
    type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

type AdminNavItem = {
    label: string;
    href: string;
    description: string;
    icon: LucideIcon;
};

const ADMIN_NAV_ITEMS: AdminNavItem[] = [
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
        href: "/admin/podcasts",
        description: "Ownership review",
        icon: Podcast,
    },
];

const MENU_ID = "admin-navigation-menu";

export default function AdminNavigationMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isOpen) return;

        function closeOnOutsidePointerDown(event: PointerEvent) {
            if (
                event.target instanceof Node &&
                !menuRef.current?.contains(event.target)
            ) {
                setIsOpen(false);
            }
        }

        function closeOnEscape(event: KeyboardEvent) {
            if (event.key === "Escape") setIsOpen(false);
        }

        window.addEventListener("pointerdown", closeOnOutsidePointerDown);
        window.addEventListener("keydown", closeOnEscape);

        return () => {
            window.removeEventListener(
                "pointerdown",
                closeOnOutsidePointerDown,
            );
            window.removeEventListener("keydown", closeOnEscape);
        };
    }, [isOpen]);

    return (
        <div ref={menuRef} className="relative">
            <button
                type="button"
                aria-controls={MENU_ID}
                aria-expanded={isOpen}
                aria-label="Admin navigation"
                onClick={() => setIsOpen((open) => !open)}
                className="flex cursor-pointer list-none items-center gap-2 rounded-md border border-copper/35 bg-white px-3 py-2 font-dmSans text-body font-semibold text-cedar shadow-sm outline-none hover:bg-copper/10 focus-visible:ring-2 focus-visible:ring-copper/40"
            >
                <Menu className="h-5 w-5 text-copper-dark" />
                Menu
            </button>
            {isOpen ? (
                <nav
                    id={MENU_ID}
                    aria-label="Admin navigation"
                    className="absolute left-0 z-30 mt-2 w-72 overflow-hidden rounded-md border border-copper/25 bg-white shadow-xl"
                >
                    {ADMIN_NAV_ITEMS.map((item) => {
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="flex items-center gap-3 border-b border-copper/10 px-4 py-3 text-left last:border-b-0 hover:bg-coconut-cream/60"
                                onClick={() => setIsOpen(false)}
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
            ) : null}
        </div>
    );
}
