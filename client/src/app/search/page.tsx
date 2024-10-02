import moment from 'moment';
import { SearchResultResponse } from "@/interfaces/searchResult.interface";
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults } from "@/actions/getSearchResults";

export default async function SearchResultsPage({
  searchParams,
}: {
  searchParams?: {
    page?: string;
    location?: string;
    startDate?: string;
    endDate?: string;
    filter?: string;
  };
}) {

  const formattedStartDate = searchParams?.startDate ? moment(new Date(searchParams.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = searchParams?.endDate ? moment(new Date(searchParams.endDate)).format('ll') : moment(new Date()).format('ll')

  const range = `between ${formattedStartDate} - ${formattedEndDate}`

  const searchResults = await getSearchResults({
    currentPage: searchParams?.page || '1',
    location: searchParams?.location || 'New York',
    startDate: formattedStartDate,
    endDate: formattedEndDate,
    filter: searchParams?.filter || 'popularity'
  }) as SearchResultResponse

  return (
    <div>
      <section className="flex-grow pt-5 px-6 m-5">
        <p className="text-xs text-silver-gray">{`${searchResults.totalShows} shows ${range}`}</p>
        <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`Shows in ${searchResults.city}`}</h1>
      </section>
      <section>
        <SearchResultsTable searchResults={searchResults} selectedFilter={searchParams?.filter} />
      </section>
    </div>
  )
}
