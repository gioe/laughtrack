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
            ? "font-inter text-gray-900 cursor-pointer"
            : "font-inter text-gray-500";
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
                    <MenuButton
                        className="group flex w-full items-center justify-between rounded-lg py-2 pl-3 pr-3.5 leading-7
                    text-copper font-inter hover:bg-gray-50"
                    >
                        Sort
                        <ChevronDownIcon
                            aria-hidden="true"
                            className="h-5 w-5 flex-none text-soft-charcoal"
                        />
                    </MenuButton>
                </div>

                <MenuItems
                    transition
                    className="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-lg
     shadow-2xl ring-1 ring-black ring-opacity-5 transition focus:outline-none
     data-[closed]:scale-95 data-[closed]:transform data-[closed]:opacity-0 data-[enter]:duration-100
      data-[leave]:duration-75 data-[enter]:ease-out data-[leave]:ease-in"
                >
                    <div className="py-1 bg-white rounded-lg">
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
