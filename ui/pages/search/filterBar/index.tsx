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
        <div className="w-full">
            <div className="mx-10">
                <div className="w-full max-w-4xl">{children}</div>

                <div className="flex justify-between items-center">
                    <PageParamComponent itemCount={total} />

                    {/* Right Sort Dropdown */}
                    <div className="flex items-center gap-4">
                        <SortParamComponent />

                        {filters && <FilterModalButton />}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
