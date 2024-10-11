import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults, HomeSearchParams, HomeSearchResultResponse } from "@/actions/search/getSearchResults";
import FilterPageContainer, { Filter, FilterOption } from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' }
]

var clubFilter: Filter = {
  id: 'clubs',
  name: 'Clubs',
  options: []
}

export default async function CityDetailPage({
  searchParams,
}: {
  searchParams: HomeSearchParams;
}) {

  const formattedStartDate = searchParams?.startDate ? moment(new Date(searchParams.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = searchParams?.endDate ? moment(new Date(searchParams.endDate)).format('ll') : moment(new Date()).format('ll')
  const range = `between ${formattedStartDate} - ${formattedEndDate}`

  const searchResults = await getSearchResults(searchParams) as HomeSearchResultResponse;

  clubFilter = {
    ...clubFilter,
    options: searchResults.clubs.map((clubName: string) => {
      return {
        value: clubName.toLowerCase(),
        label: clubName,
        selected: false
      } as FilterOption;
    })
  }

  return (

    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        searchPlaceholder={'Search for comedian'}
        query={searchParams.query}
        totalPages={searchResults.totalPages}
        filters={[clubFilter]}
        sortOptions={sortOptions}
        title={`${searchResults.totalShows} shows in ${searchResults.entity.name} ${range}`}
        child={
          <SearchResultsTable searchResults={searchResults} />
        } />
    </main>
  )
}
