"use client";

import React, { useState } from "react";
import { X } from "lucide-react";
import { useFilterModal } from "@/hooks/modalState";
import { useFilterProvider } from "@/contexts/FilterDataProvider";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Navigator } from "@/objects/class/navigate/Navigator";
import { Filter } from "@/objects/class/filter/Filter";

const FilterModal = () => {
    const paramsHelper = new SearchParamsHelper(useSearchParams());
    const navigator = new Navigator(usePathname(), useRouter());

    const filterModal = useFilterModal();
    const { filters } = useFilterProvider();

    const [selectedTypes, setSelectedTypes] = useState(
        filters.filter((filter) => filter.selected),
    );

    const handleFilterOptionClick = (option: Filter) => {
        let updates: Filter[] = [];
        if (selectedTypes.includes(option)) {
            updates = selectedTypes.filter((t) => t !== option);
            setSelectedTypes(updates);
        } else {
            updates = [...selectedTypes, option];
            setSelectedTypes(updates);
        }
        let paramValue = updates.map((update) => update.display).join(",");
        paramsHelper.setParamValue("filters", paramValue);
        navigator.replaceRoute(paramsHelper.asParamsString());
    };

    if (!filterModal.isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="w-full max-w-md bg-ivory rounded-lg p-6 m-4">
                <div className="flex justify-between items-center mb-2">
                    <h2 className="text-[26px] font-bold font-chivo text-gray-800">
                        Filter Results
                    </h2>
                    <button
                        onClick={() => filterModal.onClose()}
                        className="text-gray-500 hover:text-gray-700"
                    >
                        <X size={20} />
                    </button>
                </div>

                <p className="text-gray-600 mb-4 font-dmSans text-[16px]">
                    Select options to refine search
                </p>

                <div className="mb-6 pt-7">
                    <h3 className="text-[18px] font-bold font-chivo text-gray-800 mb-3 pb-3">
                        Filter By
                    </h3>
                    <div className="flex flex-wrap gap-2">
                        {filters.map((option) => (
                            <button
                                key={option.id}
                                onClick={() => handleFilterOptionClick(option)}
                                className={`px-4 py-2 rounded-full text-[13px] font-bold font-dmSans transition-colors
                  ${
                      selectedTypes.includes(option)
                          ? "bg-copper text-white border border-copper hover:border-white"
                          : "bg-ivory text-gray-700 border border-gray-300 hover:border-copper"
                  }`}
                            >
                                {option.display}
                            </button>
                        ))}
                    </div>
                </div>
                {/*
                <button className="w-full font-dmSans bg-copper text-ivory py-3 rounded-lg font-bold text-[16px] border-copper border hover:border-white transition-colors">
                    Show 26 Results
                </button> */}

                <button
                    onClick={() => filterModal.onClose()}
                    className="w-full text-gray-600 mt-4 hover:text-gray-800 transition-colors font-dmSans text-16 font-medium"
                >
                    Close
                </button>
            </div>
        </div>
    );
};

export default FilterModal;
