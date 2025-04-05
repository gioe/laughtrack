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
    const entityType = VARIANT_TO_ENTITY_TYPE_MAP[variant] ?? EntityType.Show;
    const sortOptions = getSortOptionsForEntityType(entityType);
    return <SortParamComponent sortOptions={sortOptions} />;
};

const FilterBar = ({ variant, total, filters }: FilterBarProps) => {
    return (
        <div className="w-full bg-coconut-cream/30">
            {/* Search Section */}
            <div className="w-full border-b border-black/5">
                <div className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
                    {getSearchBar(variant)}
                </div>
            </div>

            {/* Controls Bar */}
            <div className="w-full border-b border-black/5">
                <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
                    <div className="flex flex-col sm:flex-row gap-4">
                        {/* Left Side - Sort & Filter Controls */}
                        <div className="flex items-center gap-6 order-2 sm:order-1">
                            <div className="flex items-center gap-3">
                                <span className="text-sm font-medium text-copper">
                                    Sort by:
                                </span>
                                <div className="text-copper">
                                    {getSortOptions(variant)}
                                </div>
                            </div>

                            {filters && (
                                <div
                                    className="[&>button]:px-4 [&>button]:py-2 [&>button]:bg-copper/10 [&>button]:rounded-full
                                              [&>button:hover]:bg-copper/20 [&>button]:transition-colors [&>button]:duration-200"
                                >
                                    <FilterModalButton />
                                </div>
                            )}
                        </div>

                        {/* Right Side - Pagination */}
                        <div className="flex-shrink-0 order-1 sm:order-2 sm:ml-auto">
                            <PageParamComponent itemCount={total} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
