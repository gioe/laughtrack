import { FetchPaginatedComedianParams, getPaginatedComedians, GetPaginatedComediansResponse } from "@/actions/comedians/getPaginatedComedians";
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
  searchParams?: FetchPaginatedComedianParams;
}) {

  const response = await getPaginatedComedians(searchParams) as GetPaginatedComediansResponse
  const title = `Browsing ${response.totalComedians} comedians`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        totalItems={response.totalComedians}
        defaultSort={sortOptions[0].value}
        searchPlaceholder={'Search for comics'}
        totalPages={response.totalPages}
        query={searchParams?.query}
        sortOptions={sortOptions}
        child={
          <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
            <ComedianTable response={response} />
          </Suspense>
        } />
    </main>
  );
}

