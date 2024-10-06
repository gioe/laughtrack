'use client';

import { useState } from 'react';
import { PaginationComponent } from "../pagination/Pagination";
import FilterComponent from "../filters/FilterComponent";
import ShowInfoCard from "./cards/ShowInfoCard";
import { HomeSearchResultInterface } from '@/interfaces/searchResult.interface';
import { LineupItem } from '@/interfaces/comedian.interface copy';
import { ShowInterface } from '@/interfaces/show.interface';

interface SearchResultsTableProps {
    searchResults: HomeSearchResultInterface;
    selectedFilter?: string
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
    selectedFilter
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    return (
        <main className="flex flex-col m-5">
            <div className="flex flex-row">
                <FilterComponent selectedFilter={selectedFilter} />
                <PaginationComponent pageCount={10} />
            </div>
            <section className="flex-grow pt-14 px-6">
                <div className="relative grid grid-cols-2 gap-5">
                    {searchResults.shows.map((result: ShowInterface) => {
                        return (
                            <ShowInfoCard
                                key={result.id}
                                show={result} />
                        )
                    })}
                </div>

            </section>
        </main>
    )

}

export default SearchResultsTable;