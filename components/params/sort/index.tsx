"use client";

import { Menu, MenuButton, MenuItem, MenuItems } from "@headlessui/react";
import { useState } from "react";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { QueryProperty } from "../../../objects/enum";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { cn } from "../../../util/tailwindUtil";
import { SortOptionInterface } from "../../../objects/interface";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { Navigator } from "../../../objects/class/navigate/Navigator";
import { useDataProvider } from "../../../contexts/EntityPageDataProvider";

export function SortParamComponent() {
    const { sortOptions } = useDataProvider();
    const paramsHelper = new SearchParamsHelper(useSearchParams());

    const navigator = new Navigator(usePathname(), useRouter());

    const defaultOption = sortOptions.find(
        (value) =>
            value.value == paramsHelper.getParamValue(QueryProperty.Sort) &&
            value.direction ==
                paramsHelper.getParamValue(QueryProperty.Direction),
    );

    const [selectedSortingOption, setSelectedSortingOption] = useState(
        defaultOption ?? sortOptions[0],
    );

    const evaluateEquivalence = (
        a: SortOptionInterface,
        b: SortOptionInterface,
    ) => {
        return a.value == b.value && a.direction == b.direction;
    };

    const determineStyling = (option: SortOptionInterface) => {
        return evaluateEquivalence(option, selectedSortingOption)
            ? "font-medium text-gray-900 cursor-pointer"
            : "text-gray-500";
    };

    const modifySortParam = (sortValue: SortOptionInterface) => {
        paramsHelper.setParamValue(QueryProperty.Sort, sortValue.value);
        paramsHelper.setParamValue(
            QueryProperty.Direction,
            sortValue.direction,
        );
        navigator.replaceRoute(paramsHelper.asParamsString());
        setSelectedSortingOption(sortValue);
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
                        {sortOptions.map((option) => (
                            <MenuItem key={option.name}>
                                <h1
                                    onClick={() => modifySortParam(option)}
                                    className={cn(
                                        determineStyling(option),
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
