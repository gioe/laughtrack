"use client";

import {
    Dialog,
    DialogPanel,
    Disclosure,
    DisclosureButton,
} from "@headlessui/react";
import { ChevronDownIcon } from "@heroicons/react/24/solid";
import { HeaderItem } from "../../navbar/headerItem";
import { useStyleContext } from "@/contexts/StyleProvider";
import { twMerge } from "tailwind-merge";
import { text } from "stream/consumers";

interface HeaderItemProps {
    title: string;
    href: string;
    highlighted: boolean;
}

export function SideDrawerItem({ title, href, highlighted }: HeaderItemProps) {
    const baseClasses = `text-[16px] font-semibold font-dmSans ${highlighted ? "opacity-100" : "opacity-50 hover:opacity-75"}`;

    return (
        <a href={href} className={twMerge(baseClasses, "text-black")}>
            <Disclosure as="div" className="-mx-3">
                <DisclosureButton
                    className="group flex w-full
                                items-center justify-between
                                rounded-lg py-2 pl-3 pr-3.5 text-base leading-7
                                 hover:bg-gray-300"
                >
                    {title}
                </DisclosureButton>
            </Disclosure>
        </a>
    );
}
