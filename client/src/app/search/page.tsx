import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import { getSearchResults, HomeSearchParams } from "@/actions/search/getSearchResults";

export default async function SearchResultsPage({
  params,
}: {
  params: HomeSearchParams;
}) {

  const formattedStartDate = params?.startDate ? moment(new Date(params.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = params?.endDate ? moment(new Date(params.endDate)).format('ll') : moment(new Date()).format('ll')

  const range = `between ${formattedStartDate} - ${formattedEndDate}`

  const searchResults = await getSearchResults(params)

  return (
    <main className="flex-grow pt-14 m-5 px-6 bg-shark">
      <section className="flex-grow pt-5 px-6 m-5">
        <p className="text-xs text-silver-gray">{`${searchResults.dates.length} shows ${range}`}</p>
        <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`Shows in ${searchResults.city}`}</h1>
      </section>
      <section>
        <SearchResultsTable searchResults={searchResults} />
      </section>
    </main>
  )
}
