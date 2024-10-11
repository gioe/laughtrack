import { FetchComedianParams, getComedians, GetComediansResponse } from "@/actions/comedians/getComedians";
import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";
import FilterPageContainer, { FilterOption } from "@/components/custom/filters/FilterPageContainer";

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetical' },
]

export default async function AllComediansPage({
  searchParams,
}: {
  searchParams?: FetchComedianParams;
}) {

  const response = await getComedians(searchParams) as GetComediansResponse
  const title = `Browsing ${response.totalComedians} comedians`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        defaultSort={sortOptions[0].value}
        title={title}
        searchPlaceholder={'Search for comics'}
        totalPages={response.totalPages}
        query={searchParams?.query}
        filterOptions={[]}
        sortOptions={sortOptions}
      child={
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ComedianTable response={response} />
      </Suspense>
      } />
    </main>
  );
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
