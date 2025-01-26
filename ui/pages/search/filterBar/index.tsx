"use client";

import { useFilterProvider } from "@/contexts/FilterDataProvider";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import { SortParamComponent } from "@/ui/components/params/sort";

interface FilterBarProps {
    children: React.ReactNode;
    total: number;
}
const FilterBar = ({ children, total }: FilterBarProps) => {
    const { filters } = useFilterProvider();

    return (
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between mx-24">
            <div className="flex flex-col items-start gap-7 lg:gap-2 basis-1/2">
                {children}
                <PageParamComponent itemCount={total} />
            </div>
            <div className="flex flex-col pt-7 gap-7 lg:flex-row">
                <SortParamComponent />
                {filters.length > 0 && <FilterModalButton />}
            </div>
        </div>
    );
};

export default FilterBar;
