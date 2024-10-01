'use client';

import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import { useState } from 'react';
import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowDetailsInterface } from "@/interfaces/show.interface";
import SearchResultsFilters from "../filters/SearchResultsFilters";
import { PaginationComponent } from "../Pagination";

interface SearchResultsTableProps {
    searchResults: SearchResultResponse;
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
}) => {

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);



    return (
        <main className="flex flex-col m-5">
                <div className="flex flex-row">
                    <SearchResultsFilters cities={[]} />
                    <PaginationComponent pageCount={10} />
                </div>
            <section className="flex-grow pt-14 px-6">
                <div className="flex flex-col">
                    {searchResults.shows.map((result: ShowDetailsInterface) => {
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