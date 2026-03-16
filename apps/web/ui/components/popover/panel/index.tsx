import React from "react";
import { PopoverPanel } from "@headlessui/react";

export interface NavbarPopoverItemModel {
    name: string;
    description: string;
    href: string;
    icon: React.ElementType;
}

interface NavbarPopoverItemProps {
    items: NavbarPopoverItemModel[];
}

const NavbarPopoverItem: React.FC<NavbarPopoverItemProps> = ({ items }) => {
    return (
        <>
            <PopoverPanel
                transition
                className="absolute -left-8 top-full z-10 mt-3 w-screen max-w-md overflow-hidden rounded-2xl
                 bg-white shadow-xl ring-1 ring-black/10 transition
                 data-[closed]:translate-y-2 data-[closed]:scale-95 data-[closed]:opacity-0
                 data-[enter]:duration-300 data-[leave]:duration-200
                 data-[enter]:ease-out data-[leave]:ease-in"
            >
                <div className="p-3">
                    {items.map((item) => (
                        <div
                            key={item.name}
                            className="group relative flex items-center gap-x-6
                            rounded-xl p-4 text-sm leading-6 transition-colors duration-150
                            hover:bg-copper/5 cursor-pointer"
                        >
                            <div
                                className="flex h-11 w-11 flex-none items-center justify-center
                            rounded-xl bg-gray-50 transition-colors duration-150 group-hover:bg-copper/10"
                            >
                                <item.icon
                                    aria-hidden="true"
                                    className="h-6 w-6 text-gray-500 transition-colors duration-150
                                    group-hover:text-copper"
                                />
                            </div>
                            <div className="flex-auto">
                                <a
                                    href={item.href}
                                    className="block font-semibold text-gray-900 transition-colors duration-150
                                    group-hover:text-copper"
                                >
                                    {item.name}
                                    <span className="absolute inset-0" />
                                </a>
                                <p className="mt-1 text-gray-500">
                                    {item.description}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </PopoverPanel>
        </>
    );
};

export default NavbarPopoverItem;
