'use client';

import { useState } from 'react';
import { PaginationComponent } from "../pagination/Pagination";
import FilterComponent, { PropertyFilter } from "../filters/FilterComponent";
import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowInterface } from '@/interfaces/show.interface';
import { PaginatedShowPageInterface } from './ShowTable';

const typeFilters: PropertyFilter[] = [
    {
        key: "date_time",
        label: "Date"
    },
    {
        key: "popularity_score",
        label: "Popularity"
    }
]

interface SearchResultsTableProps {
    searchResults: PaginatedShowPageInterface;
    selectedFilter?: string
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
    selectedFilter,
}) => {

    return (
        <main className="flex flex-col">
            <div className="flex flex-row">
                { searchResults.entity.dates.length > 1 && <FilterComponent propertyFilters={typeFilters} selectedFilter={selectedFilter} />}
                { searchResults.totalPages > 0 && <PaginationComponent pageCount={searchResults.totalPages} /> }
            </div>
            <section className="flex-grow pt-5 px-6">
                <div className="relative grid grid-cols-1 gap-5">
                    {searchResults.entity.dates.map((result: ShowInterface) => {
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