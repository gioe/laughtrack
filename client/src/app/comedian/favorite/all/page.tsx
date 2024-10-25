import ComedianTable from "@/components/custom/tables/ComedianTable";
import { Suspense } from 'react';
import { FilterParams } from '@/interfaces/filterParams.interface';
import { LineupItem } from '@/interfaces/lineupItem.interface';
import { ComedianInterface } from '@/interfaces/comedian.interface';
import { PUBLIC_ROUTES } from '@/lib/routes';
import { executePost } from "@/actions/executePost";

export interface FetchFavoriteComedianParams extends FilterParams { }

export interface GetComediansResponse {
  comedians: ComedianInterface[] | LineupItem[]
  query?: string;
}

export async function getFavoriteComedians(params?: FetchFavoriteComedianParams) {
  const favoriteComediansUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_FAVORITE_COMEDIANS
  return executePost<GetComediansResponse>(favoriteComediansUrl, {
    query: params?.query ?? "",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10",
  })
}

export default async function FavoriteComediansPage(
  props: {
    searchParams?: Promise<FetchFavoriteComedianParams>;
  }
) {
  const searchParams = await props.searchParams;

  const response = await getFavoriteComedians(searchParams)

  return (
    <main className="flex-grow pt-5 bg-shark">
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ComedianTable response={response} />
      </Suspense>
    </main>
  );
}
