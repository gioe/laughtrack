import { Suspense } from 'react';
import ClubTable from "@/components/custom/tables/ClubTable";
import FilterPageContainer, { FilterOption } from '@/components/custom/filters/FilterPageContainer';
import { ClubInterface } from "@/interfaces/club.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { executePost } from '@/actions/executeGet';

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetical' }
]

export interface GetClubsParams extends FilterParams {
  city?: string,
}

export interface GetClubsResponse {
  clubs: ClubInterface[]
  totalClubs: number;
  cities: string[]
}

export async function getClubs(params?: GetClubsParams) {

  const getClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_CLUBS

  return executePost<GetClubsResponse>(getClubsUrl, {
    query: params?.query ?? "",
    sort: params?.sort ?? "date",
    page: params?.page ?? "0",
    city: params?.city ?? "",
    rows: params?.rows ?? "10"
  })
}

export default async function AllClubsPage(
  props: {
    searchParams?: Promise<GetClubsParams>;
  }
) {

  const searchParams = await props.searchParams;
  const response = await getClubs(searchParams);

  const title = `Browsing ${response.totalClubs} clubs`
  const filters = buildFilters(response, searchParams)

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        itemCount={response.totalClubs}
        title={title}
        defaultSort={sortOptions[0].value}
        searchPlaceholder={'Search for clubs'}
        query={searchParams?.query}
        filterOptions={filters}
        sortOptions={sortOptions}
        child={
          <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
            <ClubTable response={response} />
          </Suspense>
        } />
    </main>
  );
}

const buildFilters = (results: GetClubsResponse, params?: GetClubsParams) => {

  const cityFilter = {
    id: 'city',
    name: 'Cities',
    options: results.cities.map((cityName: string) => {
      return {
        value: cityName.toLowerCase(),
        label: cityName,
        selected: params?.city?.includes(cityName.toLowerCase())
      } as FilterOption;
    })
  }

  return [cityFilter];
}