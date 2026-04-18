"use client";

import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { SortOptionInterface } from "@/objects/interface";
import { cn } from "@/util/tailwindUtil";
import { Menu as MenuIcon } from "lucide-react";
import { useSortParams } from "./hooks/useSortParams";

interface SortComponentProps {
    sortOptions: SortOptionInterface[];
    isAdmin?: boolean;
}

// Literal ids (not useId) — HeadlessUI's internal useId was drifting across
// SSR/hydration because of upstream tree-shape differences, producing
// mismatched headlessui-menu-button-_R_<hash>_ values. Since only one
// SortParamComponent renders per search page, a static id is unique.
const BUTTON_ID = "sort-menu-button";
const ITEMS_ID = "sort-menu-items";

export function SortParamComponent({
    sortOptions,
    isAdmin,
}: SortComponentProps) {
    const { selectedOption, updateSort, isSelected } = useSortParams(
        sortOptions,
        isAdmin,
    );

    return (
        <Menu
            as="div"
            className="flex-item items-end relative inline-block text-left"
        >
            <div>
                <MenuButton
                    id={BUTTON_ID}
                    className="group flex items-center justify-between rounded-lg
                             text-copper font-dmSans text-[16px] hover:bg-gray-50"
                >
                    <div className="flex items-center gap-2">
                        <MenuIcon size={20} />
                        <span className="pr-3">Sort</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="hidden sm:inline">
                            {selectedOption.name}
                        </span>
                        <ChevronDownIcon
                            aria-hidden="true"
                            className="h-5 w-5 flex-none text-copper"
                        />
                    </div>
                </MenuButton>
            </div>

            <MenuItems
                id={ITEMS_ID}
                transition
                anchor={{ to: "bottom start", gap: 8 }}
                className="z-10 w-40 origin-top-left rounded-lg
                          shadow-2xl ring-1 ring-black ring-opacity-5 transition focus:outline-none
                          data-[closed]:scale-95 data-[closed]:transform data-[closed]:opacity-0
                          data-[enter]:duration-100 data-[leave]:duration-75
                          data-[enter]:ease-out data-[leave]:ease-in"
            >
                <div className="py-1 bg-white rounded-lg">
                    {sortOptions.map((option) => (
                        <MenuItem key={option.name}>
                            <button
                                onClick={() => updateSort(option)}
                                className={cn(
                                    isSelected(option)
                                        ? "font-dmSans text-gray-900"
                                        : "font-dmSans text-gray-500",
                                    "block w-full text-left px-4 py-2 text-sm data-[focus]:bg-gray-100 cursor-pointer",
                                )}
                            >
                                {option.name}
                            </button>
                        </MenuItem>
                    ))}
                </div>
            </MenuItems>
        </Menu>
    );
}
