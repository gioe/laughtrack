"use client";

import { MinusIcon, PlusIcon } from "@heroicons/react/20/solid";
import {
    Disclosure,
    DisclosureButton,
    DisclosurePanel,
} from "@headlessui/react";

import { URLParam } from "../../../objects/enum";
import { FilterSection } from "../../../objects/interface/filter.interface";
import { usePathname, useRouter } from "next/navigation";
import { SearchParamsHelper } from "../../../objects/class/params/SearchParamsHelper";
import { Navigator } from "../../../objects/class/navigate/Navigator";

interface FilterOptionsComponentProps {
    sections: FilterSection[];
}

export function FilterParamComponent({
    sections,
}: FilterOptionsComponentProps) {
    const navigator = new Navigator(usePathname(), useRouter());

    const appendParam = (type: string, filter: string) => {
        SearchParamsHelper.setParamValue(URLParam.City, "");
        navigator.replaceRoute(SearchParamsHelper.asParamsString());
    };

    return (
        <form className="mt-4 border-t border-gray-200">
            {sections.length > 0 &&
                sections.map((section) => (
                    <Disclosure
                        key={section.id}
                        as="div"
                        className="border-t border-gray-200 px-4 py-6"
                    >
                        <h3 className="-mx-2 -my-3 flow-root">
                            <DisclosureButton
                                className="group flex w-full items-center
             justify-between bg-shark px-2 py-3
              text-white hover:text-gray-500"
                            >
                                <span className="font-medium text-white">
                                    {section.name}
                                </span>
                                <span className="ml-6 flex items-center">
                                    <PlusIcon
                                        aria-hidden="true"
                                        className="h-5 w-5 group-data-[open]:hidden"
                                    />
                                    <MinusIcon
                                        aria-hidden="true"
                                        className="h-5 w-5 [.group:not([data-open])_&]:hidden"
                                    />
                                </span>
                            </DisclosureButton>
                        </h3>
                        <DisclosurePanel className="pt-6">
                            <div className="space-y-2">
                                {section.options.map((option, optionIdx) => (
                                    <div
                                        key={option.value}
                                        className="flex items-center"
                                    >
                                        <input
                                            onClick={() =>
                                                appendParam(
                                                    section.id,
                                                    option.value,
                                                )
                                            }
                                            defaultValue={option.value}
                                            defaultChecked={option.selected}
                                            id={`filter-mobile-${section.id}-${optionIdx}`}
                                            name={`${section.id}[]`}
                                            type="checkbox"
                                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                        />
                                        <label
                                            htmlFor={`filter-mobile-${section.id}-${optionIdx}`}
                                            className="ml-3 min-w-0 flex-1 text-silver-gray"
                                        >
                                            {option.label}
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </DisclosurePanel>
                    </Disclosure>
                ))}
        </form>
    );
}
