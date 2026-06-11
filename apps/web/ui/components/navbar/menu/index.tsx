import { PopoverGroup } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavigationDropdown from "../dropdown";
import { Building2, MapPin, Music, Smile } from "lucide-react";

// Navigation menu items. Each per-entity dropdown links to that entity's
// search/browse page ("Browse all").
const MENU_ITEMS = {
    comedian: [
        {
            name: "Browse all",
            description:
                "Browse comedians and filter by location, sort, and more",
            href: "/comedian/search",
            icon: Smile,
        },
    ],
    club: [
        {
            name: "Browse all",
            description:
                "Browse comedy clubs and filter by location, chain, and more",
            href: "/club/search",
            icon: Building2,
        },
    ],
    show: [
        {
            name: "Browse all",
            description:
                "Browse upcoming shows with date, location, and lineup filters",
            href: "/show/search",
            icon: MapPin,
        },
    ],
    podcast: [
        {
            name: "Browse all",
            description: "Browse comedy podcasts",
            href: "/podcast/search",
            icon: Music,
        },
    ],
};

export default function NavigationMenu({ pathname }: { pathname: string }) {
    return (
        <div className="flex items-center space-x-12">
            <HeaderItem
                highlighted={pathname === "/"}
                href="/"
                title="Near Me"
            />

            <PopoverGroup className="flex items-center space-x-12">
                <NavigationDropdown
                    title="Shows"
                    items={MENU_ITEMS.show}
                    isHighlighted={pathname.includes("/show")}
                />
                <NavigationDropdown
                    title="Comedians"
                    items={MENU_ITEMS.comedian}
                    isHighlighted={pathname.includes("/comedian")}
                />
                <NavigationDropdown
                    title="Clubs"
                    items={MENU_ITEMS.club}
                    isHighlighted={pathname.includes("/club")}
                />
                <NavigationDropdown
                    title="Podcasts"
                    items={MENU_ITEMS.podcast}
                    isHighlighted={pathname.includes("/podcast")}
                />
            </PopoverGroup>
        </div>
    );
}
