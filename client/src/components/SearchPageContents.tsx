'use client';

import { SearchResult, SearchResultResponse } from "@/interfaces/searchResult.interface";
import Link from "next/link";
import InfoCard from "./InfoCard";
import MapComponent from "./MapComponent";
import { MapCoordinate } from "@/interfaces/mapCoordinate.interface";

interface SearchPageContentProps {
    searchResults: SearchResultResponse;
}

const SearchPageContents: React.FC<SearchPageContentProps> = ({
    searchResults,
}) => {

    const handlePinSelection = (coordinate: MapCoordinate | null) => {

    }

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

            <section className="hidden xl:inline-flex xl:min-w-[600px]">
                <MapComponent coordinates={searchResults.coordinates} 
                  onSelectCoordinate={handlePinSelection}/>
            </section>

        </main>
    )

}

export default SearchPageContents;