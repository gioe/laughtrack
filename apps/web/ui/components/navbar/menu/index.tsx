import { PopoverGroup } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavigationDropdown from "../dropdown";
import {
    BuildingStorefrontIcon,
    FaceSmileIcon,
    MapPinIcon,
} from "@heroicons/react/24/outline";

// Navigation menu items
const MENU_ITEMS = {
    comedian: [
        {
            name: "Search",
            description: "Search for comedians you're interested in",
            href: "/comedian/search",
            icon: FaceSmileIcon,
        },
    ],
    club: [
        {
            name: "Search",
            description: "Search for clubs you're interested in",
            href: "/club/search",
            icon: BuildingStorefrontIcon,
        },
    ],
    show: [
        {
            name: "Search",
            description: "Search for shows in your area",
            href: "/show/search",
            icon: MapPinIcon,
        },
    ],
};

export default function NavigationMenu({ pathname }: { pathname: string }) {
    return (
        <div className="flex items-center space-x-12">
            <HeaderItem highlighted={pathname === "/"} href="/" title="Home" />

            <PopoverGroup className="flex items-center space-x-12">
                <NavigationDropdown
                    title="Shows"
                    items={MENU_ITEMS.show}
                    isHighlighted={pathname.includes("/show")}
                />
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
