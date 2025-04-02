"use client";

import { EntityType } from "@/objects/enum";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import ClubSearchBar from "@/ui/components/params/search/pages/club/all";
import ClubDetailSearchBar from "@/ui/components/params/search/pages/club/detail";
import ComedianSearchBar from "@/ui/components/params/search/pages/comedian/all";
import ComedianDetailSearchBar from "@/ui/components/params/search/pages/comedian/detail";
import ShowSearchBar from "@/ui/components/params/search/pages/show/all";
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
        <div className="w-full">
            {/* Search Bar Section - Centered with background */}
            <div className="w-full bg-coconut-cream/30 border-b border-black/5 mb-6">
                <div className="max-w-7xl mx-auto px-4 py-4 md:py-6 md:px-6 lg:px-10">
                    <div className="w-full flex justify-center">
                        {getSearchBar(variant)}
                    </div>
                </div>
            </div>

            {/* Controls Section - Full width */}
            <div className="max-w-full mx-auto px-4 md:px-6 lg:px-10">
                <div className="flex flex-col xl:flex-row items-start xl:items-center gap-6">
                    {/* Left side - Results count */}
                    <div className="hidden xl:flex items-center gap-2 min-w-[250px] xl:w-auto order-2 xl:order-1">
                        <button
                            type="button"
                            className="flex items-center gap-2 text-copper font-dmSans text-[16px] whitespace-nowrap"
                        >
                            Results:
                        </button>
                        <div className="xl:block overflow-x-auto">
                            <PageParamComponent itemCount={total} />
                        </div>
                    </div>

                    {/* Controls for smaller screens - stacked vertically */}
                    <div className="flex flex-col w-full gap-4 xl:hidden">
                        <div className="flex items-center justify-between w-full">
                            <div className="text-copper">
                                {getSortOptions(variant)}
                            </div>
                            {filters && (
                                <div className="text-copper">
                                    <FilterModalButton />
                                </div>
                            )}
                        </div>
                        <div className="flex items-center gap-2 overflow-x-auto min-w-0 w-full">
                            <button
                                type="button"
                                className="flex items-center gap-2 text-copper font-dmSans text-[16px] whitespace-nowrap"
                            >
                                Results:
                            </button>
                            <div className="overflow-x-auto min-w-0">
                                <PageParamComponent itemCount={total} />
                            </div>
                        </div>
                    </div>

                    {/* Right side - Sort and Filter for large screens */}
                    <div className="hidden xl:flex items-center justify-end gap-6 flex-1 xl:w-auto order-1 xl:order-2">
                        <div className="text-copper">
                            {getSortOptions(variant)}
                        </div>

                        {filters && (
                            <div className="text-copper border-l border-copper/20 pl-6">
                                <FilterModalButton />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
