"use client";

import { EntityType } from "@/objects/enum";
import { SearchVariant } from "@/objects/enum/searchVariant";
import { SortOptionInterface } from "@/objects/interface";
import { FilterModalButton } from "@/ui/components/params/filter";
import { PageParamComponent } from "@/ui/components/params/page";
import ClubSearchBar from "@/ui/components/params/searchbar/club";
import ComedianSearchBar from "@/ui/components/params/searchbar/comedian";
import ShowSearchBar from "@/ui/components/params/searchbar/show/search";
import { SortParamComponent } from "@/ui/components/params/sort";
import { getSortOptionsForEntityType } from "@/util/sort";

interface FilterBarProps {
    variant: SearchVariant;
    total: number;
    filters: boolean;
}

const getSearchBar = (variant: SearchVariant) => {
    switch (variant) {
        case SearchVariant.AllClubs:
            return <ClubSearchBar />;
        case SearchVariant.ClubDetail:
            return <ComedianSearchBar />;
        case SearchVariant.AllComedians:
            return <ComedianSearchBar />;
        case SearchVariant.ComedianDetail:
            return <ShowSearchBar />;
        case SearchVariant.AllShows:
            return <ShowSearchBar />;
        default:
            return null;
    }
};

const getSortOptions = (variant: SearchVariant) => {
    let sortOptions: SortOptionInterface[] = [];
    switch (variant) {
        case SearchVariant.AllClubs:
            sortOptions = getSortOptionsForEntityType(EntityType.Club);
        case SearchVariant.ClubDetail:
            sortOptions = getSortOptionsForEntityType(EntityType.Show);
        case SearchVariant.AllComedians:
            sortOptions = getSortOptionsForEntityType(EntityType.Comedian);
        case SearchVariant.ComedianDetail:
            sortOptions = getSortOptionsForEntityType(EntityType.Show);
        case SearchVariant.AllShows:
            sortOptions = getSortOptionsForEntityType(EntityType.Show);
        default:
            break;
    }

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
