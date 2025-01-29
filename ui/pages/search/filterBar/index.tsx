"use client";

import { EntityType } from "@/objects/enum";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import ClubSearchBar from "@/ui/components/params/searchbar/club";
import ComedianSearchBar from "@/ui/components/params/searchbar/comedian";
import ShowSearchBar from "@/ui/components/params/searchbar/show/search";
import { SortParamComponent } from "@/ui/components/params/sort";

interface FilterBarProps {
    variant: EntityType;
    total: number;
    filters: boolean;
}

const FilterBar = ({ variant, total, filters }: FilterBarProps) => {
    const getSearchBar = (variant: EntityType) => {
        switch (variant) {
            case EntityType.Club:
                return <ClubSearchBar />;
            case EntityType.Show:
                return <ShowSearchBar />;
            case EntityType.Comedian:
                return <ComedianSearchBar />;
            default:
                return null;
        }
    };

    return (
        <div className="px-4 sm:px-6 lg:px-10 py-4">
            {/* Search bar container */}
            <div className="flex items-center justify-center w-full">
                {getSearchBar(variant)}
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
