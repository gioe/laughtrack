import { Suspense } from 'react';
import { getClubs, GetClubsParams, GetClubsResponse } from "@/actions/clubs/getClubs";
import ClubTable from "@/components/custom/tables/ClubTable";
import FilterPageContainer, { FilterOption } from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetical' }
]

export default async function AllClubsPage(
  props: {
    searchParams?: Promise<GetClubsParams>;
  }
) {
  const searchParams = await props.searchParams;

  const response = await getClubs(searchParams) as GetClubsResponse

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