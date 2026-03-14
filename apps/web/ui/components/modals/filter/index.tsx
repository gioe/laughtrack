"use client";

import React from "react";
import { FilterDTO } from "@/objects/interface";
import { Modal } from "../basic";
import { FilterChip } from "../../params/filter/chips";
import { useFilters } from "@/hooks/useFilters";
import { useFilterModal } from "@/hooks";

interface FilterModalProps {
    filters: FilterDTO[];
    total: number;
}

const FilterModal = ({ filters, total }: FilterModalProps) => {
    const filterModal = useFilterModal();
    const { handleFilterChange, handleClose } = useFilters(filters);

    const onClose = () => {
        handleClose();
        filterModal.onClose();
    };
    return (
        <Modal
            isOpen={filterModal.isOpen}
            onClose={onClose}
            title="Filter Results"
        >
            <p className="text-gray-600 mb-4 font-dmSans text-[16px] animate-fadeIn">
                Select options to refine search
            </p>

            <div className="mb-6 pt-7 animate-slideUp">
                <h3 className="text-[18px] font-bold font-gilroy-bold text-gray-800 mb-3 pb-3 border-b border-gray-100">
                    Filter By
                </h3>
                <div className="flex flex-wrap gap-2">
                    {filters.map((option) => (
                        <FilterChip
                            key={`filter-${option.id}`}
                            option={option}
                            onClick={handleFilterChange}
                        />
                    ))}
                </div>
            </div>

            <button
                onClick={onClose}
                className="w-full font-dmSans bg-copper text-ivory py-3 rounded-lg font-bold text-[16px] shadow-sm 
                transform transition-all duration-200 ease-in-out
                hover:scale-[1.02] hover:shadow-md hover:bg-copper/90 active:scale-[0.98]
                border-2 border-copper hover:border-copper/80"
            >
                {`Show ${total} Results`}
            </button>
        </Modal>
    );
};

export default FilterModal;
