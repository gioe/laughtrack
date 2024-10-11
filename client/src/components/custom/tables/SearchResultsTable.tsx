'use client';

import ShowInfoCard from "./cards/ShowInfoCard";
import { ShowInterface } from '@/interfaces/show.interface';
import { PaginatedShowPageInterface } from './ShowTable';

interface SearchResultsTableProps {
    searchResults: PaginatedShowPageInterface;
}

const SearchResultsTable: React.FC<SearchResultsTableProps> = ({
    searchResults,
}) => {

    return (
        <main className="flex flex-col">
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