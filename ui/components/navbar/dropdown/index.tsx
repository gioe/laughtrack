import { Popover, PopoverButton } from "@headlessui/react";
import { HeaderItem } from "../headerItem";
import NavbarPopoverItem from "../../popover/panel";
import { ChevronDownIcon } from "@heroicons/react/24/solid";

export default function NavigationDropdown({ title, items, isHighlighted }) {
    return (
        <Popover className="relative">
            <PopoverButton className="flex items-center gap-x-1 leading-6">
                <HeaderItem highlighted={isHighlighted} title={title} />
                <ChevronDownIcon
                    aria-hidden="true"
                    className="h-5 w-5 flex-none text-soft-charcoal"
                />
            </PopoverButton>
            <NavbarPopoverItem items={items} />
        </Popover>
    );
}
