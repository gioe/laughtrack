import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { PUBLIC_ROUTES } from "@/lib/routes";
import { executePost } from '@/actions/executeGet';

const sortOptions = [
  { name: 'Most Popular', value: 'popularity' },
  { name: 'A-Z', value: 'alphabetical' },
]

export interface GetComedianParams extends FilterParams {}

export interface GetComediansResponse {
  comedians: ComedianInterface[]
  totalComedians: number;
}

export async function getComedians(params?: GetComedianParams) {

  const getClubsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_ALL_COMEDIANS

  return executePost<GetComediansResponse>(getClubsUrl, {
    query: params?.query ?? "",
    sort: params?.sort ?? "popularity",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10"
  })

}
export default async function AllComediansPage(
  props: {
    searchParams?: Promise<GetComedianParams>;
  }
) {
  const searchParams = await props.searchParams;

  const response = await getComedians(searchParams)
  
  const title = `Browsing ${response.totalComedians} comedians`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        itemCount={response.totalComedians}
        defaultSort={sortOptions[0].value}
        searchPlaceholder={'Search for comics'}
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

