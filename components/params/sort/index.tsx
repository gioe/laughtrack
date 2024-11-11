"use client";

import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { useState } from "react";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { useSearchParams } from "next/navigation";
import { URLParam } from "../../../util/enum";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "../../../util/tailwindUtil";
import { SortOptionInterface } from "../../../objects/interfaces";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";

interface SortParamComponentProps {
    options: SortOptionInterface[];
}

export function SortParamComponent({ options }: SortParamComponentProps) {
    const params = LaughtrackSearchParams.asClientSideParams(
        useSearchParams(),
        usePathname(),
        useRouter(),
    );

    const [selectedSort, setSelectedSort] = useState(
        params.getParamValue(URLParam.Sort),
    );

    const modifySortParam = (sortValue: string) => {
        params.setParamValue(URLParam.Sort, sortValue);
        params.replaceRoute();
        setSelectedSort(sortValue);
    };

    return (
        <div>
            <Menu
                as="div"
                className="flex-item items-end relative inline-block text-left"
            >
                <div>
                    <MenuButton className="group inline-flex justify-center text-sm font-medium text-gray-300 hover:text-gray-500">
                        Sort
                        <ChevronDownIcon
                            aria-hidden="true"
                            className="-mr-1 ml-1 h-5 w-5 flex-shrink-0 text-gray-400 group-hover:text-gray-500"
                        />
                    </MenuButton>
                </div>

                <MenuItems
                    transition
                    className="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-md
     bg-white shadow-2xl ring-1 ring-black ring-opacity-5 transition focus:outline-none
     data-[closed]:scale-95 data-[closed]:transform data-[closed]:opacity-0 data-[enter]:duration-100
      data-[leave]:duration-75 data-[enter]:ease-out data-[leave]:ease-in"
                >
                    <div className="py-1">
                        {options.map((option) => (
                            <MenuItem key={option.name}>
                                <h1
                                    onClick={() =>
                                        modifySortParam(option.value)
                                    }
                                    className={cn(
                                        option.value == selectedSort
                                            ? "font-medium text-gray-900 cursor-pointer"
                                            : "text-gray-500",
                                        "block px-4 py-2 text-sm data-[focus]:bg-gray-100 cursor-pointer",
                                    )}
                                >
                                    {option.name}
                                </h1>
                            </MenuItem>
                        ))}
                    </div>
                </MenuItems>
            </Menu>
        </div>
    );
}
