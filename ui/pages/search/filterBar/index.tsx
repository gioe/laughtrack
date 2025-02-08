"use client";

import { EntityType } from "@/objects/enum";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import ClubSearchBar from "@/ui/components/params/searchbar/club/all";
import ClubDetailSearchBar from "@/ui/components/params/searchbar/club/detail";
import ComedianSearchBar from "@/ui/components/params/searchbar/comedian/all";
import ComedianDetailSearchBar from "@/ui/components/params/searchbar/comedian/detail";
import ShowSearchBar from "@/ui/components/params/searchbar/show/search";
import { SortParamComponent } from "@/ui/components/params/sort";
import { getSortOptionsForEntityType } from "@/util/sort";

const VARIANT_TO_ENTITY_TYPE_MAP = {
    [SearchVariant.AllClubs]: EntityType.Club,
    [SearchVariant.ClubDetail]: EntityType.Show,
    [SearchVariant.AllComedians]: EntityType.Comedian,
    [SearchVariant.ComedianDetail]: EntityType.Show,
    [SearchVariant.AllShows]: EntityType.Show,
} as const;

const VARIANT_TO_SEARCH_BAR_MAP = {
    [SearchVariant.AllClubs]: ClubSearchBar,
    [SearchVariant.ClubDetail]: ClubDetailSearchBar,
    [SearchVariant.AllComedians]: ComedianSearchBar,
    [SearchVariant.ComedianDetail]: ComedianDetailSearchBar,
    [SearchVariant.AllShows]: ShowSearchBar,
} as const;

interface FilterBarProps {
    variant: SearchVariant;
    total: number;
    filters: boolean;
}

const getSearchBar = (variant: SearchVariant) => {
    const SearchBarComponent = VARIANT_TO_SEARCH_BAR_MAP[variant];
    return SearchBarComponent ? <SearchBarComponent /> : null;
};

const getSortOptions = (variant: SearchVariant) => {
    const entityType = VARIANT_TO_ENTITY_TYPE_MAP[variant] ?? EntityType.Show; // Default to Show if variant not found
    const sortOptions = getSortOptionsForEntityType(entityType);

    return <SortParamComponent sortOptions={sortOptions} />;
};

const FilterBar = ({ variant, total, filters }: FilterBarProps) => {
    return (
        <div className="px-4 sm:px-6 lg:px-10 py-4">
            <div className="flex items-center justify-center w-full">
                {getSearchBar(variant)}
            </div>

            <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex justify-center sm:justify-start w-full sm:w-auto">
                    <div className="text-amber-800">
                        <PageParamComponent itemCount={total} />
                    </div>
                </div>

                <div className="flex items-center justify-center sm:justify-end gap-4 w-full sm:w-auto">
                    <div className="text-amber-800">
                        {getSortOptions(variant)}
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
