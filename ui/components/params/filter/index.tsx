"use client";
import { useFilterModal } from "@/hooks/modalState";
import { Filter } from "lucide-react";
import { useCallback } from "react";

export function FilterModalButton() {
    const filterModal = useFilterModal();

    const openModal = useCallback(() => {
        filterModal.onOpen();
    }, [filterModal]);

    return (
        <button
            className="flex gap-2 items-center text-copper font-dmSans"
            type="button"
            onClick={openModal}
        >
            <Filter size={20} />
            <span className="hidden sm:inline font-dmSans text-[16px]">
                Filter Results
            </span>
        </button>
    );
}
