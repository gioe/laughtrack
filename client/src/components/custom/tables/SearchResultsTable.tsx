'use client';

import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import { useState } from 'react';
import { LineupItemInterface, ShowDetailsInterface } from "@/interfaces/show.interface";
import { PaginationComponent } from "../pagination/Pagination";
import { ComedianFilterChipInterface } from "@/interfaces/comedian.interface";
import { ClubFilterChipInterface } from "@/interfaces/club.interface";
import FilterComponent from "../filters/FilterComponent";
import ShowInfoCard from "./cards/ShowInfoCard";

interface SearchResultsTableProps {
    searchResults: SearchResultResponse;
    selectedFilter?: string
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
    selectedFilter
}) => {

    var comedians: ComedianFilterChipInterface[] = []
    var clubs: ClubFilterChipInterface[] = []

    searchResults.shows.forEach((show: ShowDetailsInterface) => {
        const comedians = show.lineup.flatMap((item: LineupItemInterface) => item.name);
        comedians.concat(comedians)
        clubs.push(show.club)
    })

    const [isDrawerOpen, setIsDrawerOpen] = useState(false);

    return (
        <main className="flex flex-col m-5">
            <div className="flex flex-row">
                <FilterComponent selectedFilter={selectedFilter} comedians={comedians} clubs={clubs} />
                <PaginationComponent pageCount={10} />
            </div>
            <section className="flex-grow pt-14 px-6">
                <div className="relative grid grid-cols-2 gap-5">
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