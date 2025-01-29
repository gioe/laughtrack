"use client";

import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import { SortParamComponent } from "@/ui/components/params/sort";

interface FilterBarProps {
    children: React.ReactNode;
    total: number;
    filters: boolean;
}

const FilterBar = ({ children, total, filters }: FilterBarProps) => {
    return (
        <div className="px-4 sm:px-6 lg:px-10 py-4">
            {/* Search bar container */}
            <div className="flex items-center justify-center w-full">
                {children}
            </div>

            {/* Controls container */}
            <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                {/* Rows per page - centered on mobile */}
                <div className="flex justify-center sm:justify-start w-full sm:w-auto">
                    <div className="text-amber-800">
                        <PageParamComponent itemCount={total} />
                    </div>
                </div>

                {/* Sort and filter controls */}
                <div className="flex items-center justify-center sm:justify-end gap-4 w-full sm:w-auto">
                    <div className="text-amber-800">
                        <SortParamComponent />
                    </div>

                    {filters && (
                        <div className="text-amber-800">
                            <FilterModalButton />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
