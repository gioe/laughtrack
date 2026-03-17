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

// Variants that use infinite scroll — no pagination controls needed
const INFINITE_SCROLL_VARIANTS = new Set([
    SearchVariant.AllClubs,
    SearchVariant.AllComedians,
    SearchVariant.AllShows,
]);

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
        <div className="sticky top-0 z-20 w-full bg-coconut-cream border-b border-black/5">
            <div
                className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8"
                role="search"
                aria-label="Search and filter results"
            >
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                    {/* Search input — full-width on mobile, flex-1 on sm+ */}
                    <div className="sm:flex-1">{getSearchBar(variant)}</div>

                    {/* Controls row: [sort · filter · count] | [pagination] */}
                    <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap sm:shrink-0">
                        {/* Search controls cluster */}
                        <div className="flex items-center gap-3">
                            <div className="text-copper">
                                {getSortOptions(variant)}
                            </div>

                            {filters > 0 && (
                                <FilterModalButton filterCount={filters} />
                            )}

                            <span className="hidden sm:block text-sm text-copper/60 whitespace-nowrap">
                                {total.toLocaleString()} results
                            </span>
                        </div>

                        {/* Separator */}
                        <div
                            className="hidden sm:block mx-1 h-5 w-px bg-black/15 shrink-0"
                            aria-hidden="true"
                        />

                        {/* Pagination — hidden for infinite-scroll variants */}
                        {!INFINITE_SCROLL_VARIANTS.has(variant) && (
                            <PageParamComponent itemCount={total} />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default FilterBar;
