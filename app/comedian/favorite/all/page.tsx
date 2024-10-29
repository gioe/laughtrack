import ComedianTable from "../../../../components/custom/tables/ComedianTable";
import { Suspense } from 'react';
import { SearchParams } from '../../../../interfaces/searchParams.interface';
import { ComedianInterface } from '../../../../interfaces/comedian.interface';
import { PUBLIC_ROUTES } from '../../../../util/routes';
import { executePost } from "../../../../actions/executePost";
import { generateUrl } from "../../../../util/urlUtil";

interface GetComediansResponse {
  comedians: ComedianInterface[];
  query?: string;
}

async function getFavoriteComedians(params?: SearchParams) {

  const favoriteComediansUrl = generateUrl(PUBLIC_ROUTES.GET_FAVORITE_COMEDIANS)

  return executePost<GetComediansResponse>(favoriteComediansUrl, {
    query: params?.query ?? "",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10",
  })
}

export default async function FavoriteComediansPage(
  props: {
    searchParams?: Promise<SearchParams>;
  }
) {
  const searchParams = await props.searchParams;

  const { comedians } = await getFavoriteComedians(searchParams)

  return (
    <main className="flex-grow pt-5 bg-shark">
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ComedianTable comedians={comedians} />
      </Suspense>
    </main>
  );
}
