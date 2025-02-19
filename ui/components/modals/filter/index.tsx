"use client";

import React from "react";
import { FilterDTO } from "@/objects/interface/filter.interface";
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
            <p className="text-gray-600 mb-4 font-dmSans text-[16px]">
                Select options to refine search
            </p>

            <div className="mb-6 pt-7">
                <h3 className="text-[18px] font-bold font-chivo text-gray-800 mb-3 pb-3">
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
                className="w-full font-dmSans bg-copper text-ivory py-3 rounded-lg font-bold text-[16px] border-copper border hover:border-white transition-colors"
            >
                {`Show ${total} Results`}
            </button>
        </Modal>
    );
};

export default FilterModal;
