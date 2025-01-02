/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";
import { MinusIcon, PlusIcon } from "@heroicons/react/20/solid";
import {
    Disclosure,
    DisclosureButton,
    DisclosurePanel,
} from "@headlessui/react";
import { SelectionSection } from "../../../objects/interface/selectionSection.interface";

interface MultiSelectComponentProps {
    form?: any;
    handleValueChange?: (value: string, id: number) => void;
    sections: SelectionSection[];
}

export const MultiSelectComponent: React.FC<MultiSelectComponentProps> = ({
    sections,
    handleValueChange,
}) => {
    const handleSelect = (value: string, id: number) => {
        if (handleValueChange) {
            handleValueChange(value, id);
        }
    };

    return (
        <div>
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
         justify-between bg-ivory px-2 py-3
          text-copper hover:text-gray-500"
                            >
                                <span className="font-medium text-copper">
                                    {section.displayName}
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
                                        key={option.id.toString()}
                                        className="flex items-center"
                                    >
                                        <input
                                            onClick={() =>
                                                handleSelect(
                                                    section.value,
                                                    option.id,
                                                )
                                            }
                                            defaultValue={option.id}
                                            defaultChecked={option.selected}
                                            id={`filter-mobile-${section.id}-${optionIdx}`}
                                            name={`${section.id}[]`}
                                            type="checkbox"
                                            className="h-4 w-4 rounded border-gray-300 text-copper focus:ring-copper"
                                        />
                                        <label
                                            htmlFor={`filter-mobile-${section.id}-${optionIdx}`}
                                            className="ml-3 min-w-0 flex-1 text-copper"
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
