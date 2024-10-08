import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults, HomeSearchParams } from "@/actions/search/getSearchResults";

export default async function CityDetailPage({
  searchParams,
}: {
  searchParams: HomeSearchParams;
}) {

  const formattedStartDate = searchParams?.startDate ? moment(new Date(searchParams.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = searchParams?.endDate ? moment(new Date(searchParams.endDate)).format('ll') : moment(new Date()).format('ll')

  const range = `between ${formattedStartDate} - ${formattedEndDate}`

  const searchResults = await getSearchResults(searchParams)

  return (
    <main className="flex-grow pt-5 bg-shark">
      <section className="flex-grow pt-5 px-6 m-5">
        <p className="text-xs text-silver-gray">{`${searchResults.entity.dates.length} shows ${range}`}</p>
        <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`Shows in ${searchResults.entity.name}`}</h1>
      </section>
      <section>
        <SearchResultsTable searchResults={searchResults} />
      </section>
    </main>
  )
}
