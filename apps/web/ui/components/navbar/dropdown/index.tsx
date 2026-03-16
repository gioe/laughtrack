import { Popover, PopoverButton } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavbarPopoverItem, { NavbarPopoverItemModel } from "../../popover/panel";
import { ChevronDownIcon } from "@heroicons/react/24/solid";

interface NavigationDropdownProps {
    title: string;
    items: NavbarPopoverItemModel[];
    isHighlighted: boolean;
}

export default function NavigationDropdown({
    title,
    items,
    isHighlighted,
}: NavigationDropdownProps) {
    return (
        <Popover className="relative">
            <PopoverButton className="flex items-center gap-x-1 leading-6 group">
                <HeaderItem highlighted={isHighlighted} title={title} />
                <ChevronDownIcon
                    aria-hidden="true"
                    className="h-5 w-5 flex-none text-soft-charcoal opacity-70
                    transition-all duration-300 ease-out transform group-hover:opacity-90
                    group-hover:text-copper group-data-[open]:rotate-180 group-data-[open]:opacity-90 group-data-[open]:text-copper"
                />
            </PopoverButton>
            <NavbarPopoverItem items={items} />
        </Popover>
    );
}
