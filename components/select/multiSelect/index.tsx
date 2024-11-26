/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { MinusIcon, PlusIcon } from "@heroicons/react/20/solid";
import {
    Disclosure,
    DisclosureButton,
    DisclosurePanel,
} from "@headlessui/react";
import { FilterContainer } from "../../../objects/class/tag/FilterContainer";

interface MultiSelectComponentProps {
    form?: any;
    handleValueChange?: (value: string, id: number) => void;
    containers: FilterContainer[];
}

export const MultiSelectComponent: React.FC<MultiSelectComponentProps> = ({
    containers,
    handleValueChange,
}) => {
    const handleSelect = (value: string, id: number) => {
        if (handleValueChange) {
            handleValueChange(value, id);
        }
    };

    return (
        <div>
            {containers.length > 0 &&
                containers.map((container) => (
                    <Disclosure
                        key={container.id}
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
                                    {container.displayName}
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
                                {container.options.map((option, optionIdx) => (
                                    <div
                                        key={option.id.toString()}
                                        className="flex items-center"
                                    >
                                        <input
                                            onClick={() =>
                                                handleSelect(
                                                    container.value,
                                                    option.id,
                                                )
                                            }
                                            defaultValue={option.id}
                                            defaultChecked={option.selected}
                                            id={`filter-mobile-${container.id}-${optionIdx}`}
                                            name={`${container.id}[]`}
                                            type="checkbox"
                                            className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                        />
                                        <label
                                            htmlFor={`filter-mobile-${container.id}-${optionIdx}`}
                                            className="ml-3 min-w-0 flex-1 text-silver-gray"
                                        >
                                            {option.displayName}
                                        </label>
                                    </div>
                                ))}
                            </div>
                        </DisclosurePanel>
                    </Disclosure>
                ))}
        </div>
    );
};
