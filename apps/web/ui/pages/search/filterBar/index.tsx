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
    filters: number;
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
        <div className="sticky top-0 z-10 w-full bg-coconut-cream/30 border-b border-black/5">
            <div className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8">
                <div className="flex flex-wrap sm:flex-nowrap items-center gap-3">
                    {/* Search input — full-width on mobile, flex-1 on sm+ */}
                    <div className="w-full sm:flex-1">
                        {getSearchBar(variant)}
                    </div>

                    {/* Sort + Filter — inline on sm+, second row on mobile */}
                    <div className="flex items-center gap-4 shrink-0">
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-copper">
                                Sort by:
                            </span>
                            <div className="text-copper">
                                {getSortOptions(variant)}
                            </div>
                        </div>

                        {filters > 0 && (
                            <div
                                className="[&>button]:px-4 [&>button]:py-2 [&>button]:bg-copper/10 [&>button]:rounded-full
                                          [&>button:hover]:bg-copper/20 [&>button]:transition-colors [&>button]:duration-200"
                            >
                                <FilterModalButton filterCount={filters} />
                            </div>
                        )}
                    </div>

                    {/* Pagination */}
                    <div className="shrink-0 sm:ml-auto">
                        <PageParamComponent itemCount={total} />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
