'use client';

import { SearchResult, SearchResultResponse } from "@/interfaces/searchResult.interface";
import Link from "next/link";
import InfoCard from "./SearchResultsInfoCard";

interface SearchResultsTableProps {
    searchResults: SearchResultResponse;
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
}) => {

    return (
        <main className="flex">
            <section className="flex-grow pt-14 px-6">
                <div className="flex flex-col">
                    {searchResults.shows.map((result: SearchResult) => {
                        return (
                            <Link href={result.ticket_link}>
                                <InfoCard
                                    key={result.id}
                                    result={result} />
                            </Link>
                        )
                    })}
                </div>

            </section>
        </main>
    )

}

export default SearchResultsTable;