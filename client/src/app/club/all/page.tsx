import { Suspense } from 'react';
import { getClubs, GetClubsParams, GetClubsResponse } from "@/actions/clubs/getClubs";
import ClubTable from "@/components/custom/tables/ClubTable";
import FilterPageContainer, { FilterOption } from '@/components/custom/filters/FilterPageContainer';

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetical' },
]

export default async function AllClubsPage({
  searchParams,
}: {
  searchParams?: GetClubsParams;
}) {

  const response = await getClubs(searchParams) as GetClubsResponse
  const title = `Browsing ${response.totalClubs} clubs`
  const filters = buildFilters(searchParams, response)

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer 
      title={title}
      defaultSort={sortOptions[0].value}
      searchPlaceholder={'Search for clubs'}
      totalPages={response.totalPages}
      query={searchParams?.query}
      filterOptions={filters}
      sortOptions={sortOptions}  
      child={
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ClubTable response={response}  />
        </Suspense>
      } />
    </main>
  );
}

const buildFilters = (params: any, results: any) => {

  const cityFilter = {
    id: 'cities',
    name: 'Cities',
    options: results.cities.map((cityName: string) => {
      return {
        value: cityName.toLowerCase(),
        label: cityName,
        selected: params.cities?.includes(cityName.toLowerCase())
      } as FilterOption;
    })
  }

  return [cityFilter];
}