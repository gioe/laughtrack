"use client";

import { EntityType } from "@/objects/enum";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import ClubSearchBar from "@/ui/components/params/search/pages/club/all";
import ClubDetailSearchBar from "@/ui/components/params/search/pages/club/detail";
import ComedianSearchBar from "@/ui/components/params/search/pages/comedian/all";
import ComedianDetailSearchBar from "@/ui/components/params/search/pages/comedian/detail";
import PodcastSearchBar from "@/ui/components/params/search/pages/podcast/all";
import ShowSearchBar from "@/ui/components/params/search/pages/show/all";
import { SortParamComponent } from "@/ui/components/params/sort";
import { getSortOptionsForEntityType } from "@/util/sort";
import { useUrlParams } from "@/hooks/useUrlParams";
import { FilterDTO } from "@/objects/interface";
import { ChainFilterDTO } from "@/lib/data/filters/getChainFilters";
import { X } from "lucide-react";
import { useMemo } from "react";
import {
    searchFilterChipClassName,
    searchFilterChipCompactClassName,
} from "@/ui/components/params/search/filterChipStyles";
import DateShortcutChips from "./DateShortcutChips";

// Variants that use infinite scroll — no pagination controls needed
const INFINITE_SCROLL_VARIANTS = new Set([
    SearchVariant.AllClubs,
    SearchVariant.AllComedians,
    SearchVariant.AllShows,
    SearchVariant.AllPodcasts,
]);

const VARIANT_TO_ENTITY_TYPE_MAP = {
    [SearchVariant.AllClubs]: EntityType.Club,
    [SearchVariant.ClubDetail]: EntityType.Show,
    [SearchVariant.AllComedians]: EntityType.Comedian,
    [SearchVariant.ComedianDetail]: EntityType.Show,
    [SearchVariant.AllShows]: EntityType.Show,
    [SearchVariant.AllPodcasts]: EntityType.Podcast,
} as const;

const VARIANT_TO_SEARCH_BAR_MAP = {
    [SearchVariant.AllClubs]: ClubSearchBar,
    [SearchVariant.ClubDetail]: ClubDetailSearchBar,
    [SearchVariant.AllComedians]: ComedianSearchBar,
    [SearchVariant.ComedianDetail]: ComedianDetailSearchBar,
    [SearchVariant.AllShows]: ShowSearchBar,
    [SearchVariant.AllPodcasts]: PodcastSearchBar,
} as const;

interface FilterBarProps {
    variant: SearchVariant;
    total: number;
    filterData: FilterDTO[];
    chainFilters?: ChainFilterDTO[];
    isAdmin?: boolean;
}

const getSearchBar = (variant: SearchVariant) => {
    const SearchBarComponent = VARIANT_TO_SEARCH_BAR_MAP[variant];
    return SearchBarComponent ? <SearchBarComponent /> : null;
};

const getSortOptions = (variant: SearchVariant, isAdmin = false) => {
    const entityType = VARIANT_TO_ENTITY_TYPE_MAP[variant] ?? EntityType.Show;
    const sortOptions = getSortOptionsForEntityType(entityType, isAdmin);
    return <SortParamComponent sortOptions={sortOptions} isAdmin={isAdmin} />;
};

const FilterBar = ({
    variant,
    total,
    filterData,
    chainFilters,
    isAdmin,
}: FilterBarProps) => {
    const { getTypedParam, setTypedParam } = useUrlParams();
    const isClubSearch = variant === SearchVariant.AllClubs;
    const isComedianSearch = variant === SearchVariant.AllComedians;
    const isShowSearch = variant === SearchVariant.AllShows;
    const isPodcastSearch = variant === SearchVariant.AllPodcasts;
    const includeEmptyApplies =
        isClubSearch || isComedianSearch || isPodcastSearch;
    const includeEmpty = includeEmptyApplies
        ? (getTypedParam("includeEmpty") ?? false)
        : false;

    const filtersParam: string = getTypedParam("filters") ?? "";
    const selectedSlugs = useMemo(
        () => (filtersParam ? filtersParam.split(",").filter(Boolean) : []),
        [filtersParam],
    );

    const activeFilters = useMemo(
        () => filterData.filter((f) => selectedSlugs.includes(f.slug)),
        [filterData, selectedSlugs],
    );

    // Comedian search exposes rich modal filters (zip, dates, min-shows) that
    // aren't chip-driven — count them so the modal button badge stays accurate.
    // Gated behind isComedianSearch so other variants don't pay the param reads.
    const advancedFilterCount = isComedianSearch
        ? (getTypedParam("zip") ? 1 : 0) +
          (getTypedParam("fromDate") || getTypedParam("toDate") ? 1 : 0) +
          ((getTypedParam("minUpcomingShows") ?? 0) > 0 ? 1 : 0)
        : 0;
    const filterButtonCount = activeFilters.length + advancedFilterCount;
    const showFilterButton =
        filterData.length > 0 || isComedianSearch || isPodcastSearch;

    const removeFilter = (slug: string) => {
        const updated = selectedSlugs.filter((s) => s !== slug).join(",");
        setTypedParam("filters", updated);
    };

    const chainParam: string = getTypedParam("chain") ?? "";
    const activeChain = useMemo(
        () => chainFilters?.find((c) => c.slug === chainParam) ?? null,
        [chainFilters, chainParam],
    );

    return (
        <div className="sticky top-0 z-20 w-full bg-coconut-cream border-b border-black/5">
            <div
                className="max-w-7xl mx-auto px-4 py-3 sm:px-6 lg:px-8"
                role="search"
                aria-label="Search and filter results"
            >
                {/* Date shortcut row — Shows only. Surfaces Tonight/This
                    Weekend/This Week as one-tap chips so users don't have to
                    open the WHEN calendar for the common cases (mirrors iOS
                    Search's selectedShortcut row). */}
                {isShowSearch && (
                    <div className="mb-3">
                        <DateShortcutChips />
                    </div>
                )}
                <div className="flex flex-col lg:flex-row lg:items-center gap-3">
                    {/* Search input — full-width until lg; flex-1 above so tablet keeps the input full-width instead of getting squeezed by the controls cluster */}
                    <div className="min-w-0 lg:flex-1">
                        {getSearchBar(variant)}
                    </div>

                    {/* Controls row: [sort · filter · count] | [pagination] — stacks below lg so pagination never clips on tablet */}
                    <div className="flex flex-col lg:flex-row lg:items-center gap-2 lg:shrink-0">
                        {/* Search controls cluster */}
                        <div className="flex flex-wrap items-center gap-3">
                            <div className="text-copper">
                                {getSortOptions(variant, isAdmin)}
                            </div>

                            {showFilterButton && (
                                <FilterModalButton
                                    filterCount={filterButtonCount}
                                />
                            )}

                            {isClubSearch &&
                                chainFilters &&
                                chainFilters.length > 0 && (
                                    <select
                                        value={chainParam}
                                        onChange={(e) =>
                                            setTypedParam(
                                                "chain",
                                                e.target.value,
                                            )
                                        }
                                        className={`${searchFilterChipClassName} cursor-pointer`}
                                        aria-label="Filter by chain"
                                    >
                                        <option
                                            value=""
                                            className="bg-card text-foreground"
                                        >
                                            All chains
                                        </option>
                                        {chainFilters.map((chain) => (
                                            <option
                                                key={chain.slug}
                                                value={chain.slug}
                                                className="bg-card text-foreground"
                                            >
                                                {chain.name} ({chain.clubCount})
                                            </option>
                                        ))}
                                    </select>
                                )}

                            {/* "Include all" toggles the `includeEmpty` flag, which by
                                default hides results with weak signal: clubs/comedians
                                with no upcoming shows, and podcasts with no LaughTrack
                                comedian ownership. Shows don't surface this control
                                because every show row is itself an upcoming event. */}
                            {includeEmptyApplies && (
                                <label
                                    className="flex items-center gap-1.5 text-sm text-copper/70 whitespace-nowrap cursor-pointer select-none"
                                    title={
                                        isPodcastSearch
                                            ? "Include podcasts without tracked comedian hosts"
                                            : "Include results with no upcoming shows"
                                    }
                                >
                                    <input
                                        type="checkbox"
                                        checked={includeEmpty}
                                        onChange={() =>
                                            setTypedParam(
                                                "includeEmpty",
                                                !includeEmpty,
                                            )
                                        }
                                        className="accent-copper w-3.5 h-3.5"
                                    />
                                    Include all
                                </label>
                            )}

                            <span className="hidden sm:block md:block lg:block text-sm text-copper/60 whitespace-nowrap">
                                {total.toLocaleString("en-US")} results
                            </span>
                        </div>

                        {/* Separator — only on the same row as pagination (lg+) */}
                        <div
                            className="hidden lg:block mx-1 h-5 w-px bg-black/15 shrink-0"
                            aria-hidden="true"
                        />

                        {/* Pagination — hidden for infinite-scroll variants */}
                        {!INFINITE_SCROLL_VARIANTS.has(variant) && (
                            <PageParamComponent itemCount={total} />
                        )}
                    </div>
                </div>

                {/* Active filter chips */}
                {(activeFilters.length > 0 || activeChain) && (
                    <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-black/5">
                        <span className="text-xs text-copper/60 font-dmSans">
                            Filtered by:
                        </span>
                        {activeChain && (
                            <button
                                onClick={() => setTypedParam("chain", "")}
                                className={searchFilterChipCompactClassName}
                            >
                                {activeChain.name}
                                <X size={12} />
                            </button>
                        )}
                        {activeFilters.map((filter) => (
                            <button
                                key={filter.slug}
                                onClick={() => removeFilter(filter.slug)}
                                className={searchFilterChipCompactClassName}
                            >
                                {filter.name}
                                <X size={12} />
                            </button>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default FilterBar;
