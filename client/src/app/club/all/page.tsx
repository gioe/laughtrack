import ClubTable from "@/components/custom/tables/ClubTable";
import FilterPageContainer from '@/components/custom/filters/FilterPageContainer';
import { ClubInterface } from "@/interfaces/club.interface";
import { SearchParams } from "@/interfaces/searchParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes"
import { executePost } from '@/actions/executePost';
import { SORT_OPTIONS } from '@/lib/sort';
import { Suspense } from 'react';

export interface GetClubsResponse {
  clubs: ClubInterface[]
  count: number;
  filters: string[][]
}

export async function getClubs(params?: SearchParams) {

  const getClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_CLUBS

  return executePost<GetClubsResponse>(getClubsUrl, {
    query: params?.query ?? "",
    sort: params?.sort ?? "date",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10"
  })

}

export default async function AllClubsPage(
  props: {
    searchParams?: Promise<SearchParams>;
  }
) {

  const searchParams = await props.searchParams;
  const response = await getClubs(searchParams);

  const title = `Browsing ${response.count} clubs`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        itemCount={response.count}
        sortOptions={SORT_OPTIONS.CLUB}
        child={
          <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
            <ClubTable response={response} />
          </Suspense>
        } />
    </main>
  );
}