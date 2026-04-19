"use client";
import { useFilterModal } from "@/hooks";
import { ChevronDownIcon } from "@heroicons/react/20/solid";
import { Filter } from "lucide-react";
import { useCallback } from "react";

interface FilterModalButtonProps {
    filterCount?: number;
}

export function FilterModalButton({ filterCount }: FilterModalButtonProps) {
    const filterModal = useFilterModal();

    const openModal = useCallback(() => {
        filterModal.onOpen();
    }, [filterModal]);

    return (
        <button
            className="relative flex gap-2 items-center text-copper font-dmSans"
            type="button"
            onClick={openModal}
        >
            <Filter size={20} />
            <span className="font-dmSans text-body">Filter</span>
            <ChevronDownIcon
                aria-hidden="true"
                className="h-5 w-5 flex-none text-copper"
            />
            {filterCount != null && filterCount > 0 && (
                <span
                    data-testid="filter-count-badge"
                    className="absolute -top-2 -right-2 flex items-center justify-center min-w-[1rem] h-4 px-0.5 rounded-full bg-copper text-white text-caption font-bold leading-none"
                >
                    {filterCount > 9 ? "9+" : filterCount}
                </span>
            )}
        </button>
    );
}
