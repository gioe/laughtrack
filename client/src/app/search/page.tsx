import { getUpcomingShowResults } from "@/actions/getUpcomingShows";
import { PaginationComponent } from "@/components/custom/Pagination";
import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import { UserInterface } from "@/interfaces/user.interface";
import moment from 'moment';
import SearchResultsTable from "@/components/custom/SearchResultsTable";

interface SearchPageProps {
    searchResults: SearchResultResponse;
    range: string;
    user: UserInterface
}

export default async function SearchResultsPage({
    searchParams,
  }: {
    searchParams?: {
      page?: string;
      location?: string;
      startDate?: string;
      endDate?: string;
    };
  }) {
    
    const formattedStartDate =  searchParams?.startDate ? moment(new Date(searchParams.startDate)).format('ll') :  moment(new Date()).format('ll')
    const formattedEndDate =  searchParams?.endDate ? moment(new Date(searchParams.endDate)).format('ll') :  moment(new Date()).format('ll')

    const range = `between ${formattedStartDate} - ${formattedEndDate}`

    const searchResults = await getUpcomingShowResults({
        currentPage: searchParams?.page || '1',
        location: searchParams?.location || 'New York',
        startDate: formattedStartDate,
        endDate: formattedEndDate
    }) as SearchResultResponse

    return (
        <div>
            <section className="flex-grow pt-14 px-6">
                <p className="text-xs text-silver-gray">{`${searchResults.shows.length} shows ${range}`}</p>

                <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`Shows in ${searchResults.city}`}</h1>

                <div className="hidden lg:inline-flex mb-5 space-x-3 text-silver-gray whitespace-nowrap">
                    <p className="search-filter">Sort by Popularity</p>
                    <p className="search-filter">Sort By Date</p>
                    <p className="search-filter">Sort By Surprise</p>
                </div>
                </section>
                <section>
                <SearchResultsTable searchResults={searchResults} />
                </section>
                <section>
                <PaginationComponent pageCount={searchResults.totalPages} />
                </section>
        </div>
    )
}
