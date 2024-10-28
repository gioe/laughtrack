import moment from 'moment';
import SearchResultsTable from "@/components/custom/tables/SearchResultsTable";
import FilterPageContainer from '@/components/custom/filters/FilterPageContainer';
import { PUBLIC_ROUTES } from '@/lib/routes';
import { CityInterface } from '@/interfaces/city.interface';
import { SearchParams } from '@/interfaces/searchParams.interface';
import { executePost } from '@/actions/executePost';
import { SORT_OPTIONS } from '@/lib/sort';
import { ShowProvider } from '@/interfaces/showProvider.interface';
import { Paginated } from '@/interfaces/paginated.interface';

export interface HomeSearchParams extends SearchParams {
  location: string;
  startDate: string;
  endDate: string;
}

export interface HomeSearchResultResponse extends ShowProvider, Paginated {
  city: CityInterface;
}

export async function getSearchResults(params: HomeSearchParams) {

  const upcomingShowsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.HOME_SEARCH

  return executePost<HomeSearchResultResponse>(upcomingShowsUrl, {
    location: params.location,
    startDate: params.startDate,
    endDate: params.endDate,
    sort: params.sort ?? "date",
    query: params.query ?? "",
    page: params.page ?? "0",
    rows: params.rows ?? "10"
  })
}

export default async function CityDetailPage(
  props: {
    searchParams: Promise<HomeSearchParams>;
  }
) {
  const searchParams = await props.searchParams;

  const {totalResults, city} = await getSearchResults(searchParams);
  const title = formattedTitle(searchParams, totalResults, city)

  return (

    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        itemCount={totalResults}
        sortOptions={SORT_OPTIONS.SHOW}
        child={
          <SearchResultsTable searchResults={city.dates}
          />
        }
      />
    </main>
  )

}

const formattedTitle = (params: HomeSearchParams, totalResults: number, city: CityInterface): string => {
  const formattedStartDate = params?.startDate ? moment(new Date(params.startDate)).format('ll') : moment(new Date()).format('ll')
  const formattedEndDate = params?.endDate ? moment(new Date(params.endDate)).format('ll') : moment(new Date()).format('ll')
  const range = `between ${formattedStartDate} - ${formattedEndDate}`
  return `${totalResults} shows in ${city.name} ${range}`
}
