import { PopoverGroup } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavigationDropdown from "../dropdown";
import {
    BuildingStorefrontIcon,
    FaceSmileIcon,
    MapPinIcon,
    MusicalNoteIcon,
} from "@heroicons/react/24/outline";

// Navigation menu items.
// Top-level "Search" in the nav points at /search — the cross-entity typeahead
// for users who know what they're looking for. The per-entity dropdowns below
// label their inner link "Browse all" to keep the role split visible: search
// dispatches, browse collects.
const MENU_ITEMS = {
    comedian: [
        {
            name: "Browse all",
            description:
                "Browse comedians and filter by location, sort, and more",
            href: "/comedian/search",
            icon: FaceSmileIcon,
        },
    ],
    club: [
        {
            name: "Browse all",
            description:
                "Browse comedy clubs and filter by location, chain, and more",
            href: "/club/search",
            icon: BuildingStorefrontIcon,
        },
    ],
    show: [
        {
            name: "Browse all",
            description:
                "Browse upcoming shows with date, location, and lineup filters",
            href: "/show/search",
            icon: MapPinIcon,
        },
    ],
    podcast: [
        {
            name: "Browse all",
            description: "Browse comedy podcasts",
            href: "/podcast/search",
            icon: MusicalNoteIcon,
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
            <HeaderItem
                highlighted={pathname === "/search"}
                href="/search"
                title="Search"
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
