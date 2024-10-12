import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults, HomeSearchParams, HomeSearchResultResponse } from "@/actions/search/getSearchResults";
import FilterPageContainer, { FilterOption } from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' }
]

export default async function CityDetailPage({
  searchParams,
}: {
  searchParams: HomeSearchParams;
}) {

  const searchResults = await getSearchResults(searchParams) as HomeSearchResultResponse;
  console.log(searchResults)
  const title = buildTitle(searchParams, searchResults)
  const filters = buildFilters(searchParams, searchResults)

  return (

    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        totalItems={searchResults.totalShows}
        title={title}
        searchPlaceholder={'Search for comics'}
        totalPages={searchResults.totalPages}
        query={searchParams.query}
        filterOptions={filters}
        defaultSort={sortOptions[0].value}
        sortOptions={sortOptions}
        child={ <SearchResultsTable searchResults={searchResults} />} />
    </main>
  )
}

const buildFilters =(params: any, results: any) => {

  const clubFilter = {
    id: 'clubs',
    name: 'Clubs',
    options: results.clubs.map((clubName: string) => {
      return {
        value: clubName.toLowerCase(),
        label: clubName,
        selected: params.clubs?.includes(clubName.toLowerCase())
      } as FilterOption;
    })
  }

  return [clubFilter];
}

const buildTitle = (params: any, results: any): string => {
  const formattedStartDate = params?.startDate ? moment(new Date(params.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = params?.endDate ? moment(new Date(params.endDate)).format('ll') : moment(new Date()).format('ll')
  const range = `between ${formattedStartDate} - ${formattedEndDate}`
  return `${results.totalShows} shows in ${results.entity.name} ${range}`
}
