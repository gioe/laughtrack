import { PopoverGroup } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavigationDropdown from "../dropdown";
import {
    BuildingStorefrontIcon,
    FaceSmileIcon,
} from "@heroicons/react/24/outline";

// Navigation menu items
const MENU_ITEMS = {
    comedian: [
        {
            name: "Search",
            description: "Search for comedians you're interested in",
            href: "/comedian/all",
            icon: FaceSmileIcon,
        },
    ],
    club: [
        {
            name: "Search",
            description: "Search for clubs you're interested in",
            href: "/club/all",
            icon: BuildingStorefrontIcon,
        },
    ],
};

export default function NavigationMenu({ pathname }) {
    return (
        <div className="flex items-center space-x-24">
            <HeaderItem highlighted={pathname === "/"} href="/" title="Home" />

            <PopoverGroup className="flex items-center space-x-24">
                <NavigationDropdown
                    title="Clubs"
                    items={MENU_ITEMS.club}
                    isHighlighted={pathname.includes("/club")}
                />
                <NavigationDropdown
                    title="Comedians"
                    items={MENU_ITEMS.comedian}
                    isHighlighted={pathname.includes("/comedian")}
                />
            </PopoverGroup>
        </div>
    );
}
