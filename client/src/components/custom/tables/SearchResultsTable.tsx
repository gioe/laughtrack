'use client';

import { useState } from 'react';
import { PaginationComponent } from "../pagination/Pagination";
import FilterComponent, { PropertyFilter } from "../filters/FilterComponent";
import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowInterface } from '@/interfaces/show.interface';
import { PaginatedShowInterface } from './ShowTable';

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
    searchResults: PaginatedShowInterface;
    selectedFilter?: string
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
    selectedFilter,
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    return (
        <main className="flex flex-col m-5">
            {
                searchResults.totalPages && (
                    <div className="flex flex-row">
                        <FilterComponent propertyFilters={typeFilters} selectedFilter={selectedFilter}/>
                        <PaginationComponent pageCount={searchResults.totalPages} />
                    </div>
                )
            }
            <section className="flex-grow pt-14 px-6">
                <div className="relative grid grid-cols-2 gap-5">
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