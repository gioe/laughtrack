"use client";

import { FilterDTO } from "@/objects/interface/filter.interface";
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
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mx-24">
            <div className="flex flex-col items-start gap-7 lg:gap-2 basis-1/2">
                {children}
                <PageParamComponent itemCount={total} />
            </div>
            <div className="flex flex-col pt-7 gap-7 lg:flex-row">
                <SortParamComponent />
                {filters && <FilterModalButton />}
            </div>
        </div>
    );
};

export default FilterBar;
