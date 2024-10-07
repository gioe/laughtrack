import { GetComediansResponse } from "@/actions/comedians/getComedians";
import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";
import { FetchFavoriteComedianParams, getFavoriteComedians } from "@/actions/comedians/getFavoriteComedians";

export default async function FavoriteComediansPage({
  params,
}: {
  params?: FetchFavoriteComedianParams;
}) {

  const response = await getFavoriteComedians(params)

  return (
    <main className="flex-grow pt-14 m-5 px-6 bg-shark">
      <Suspense key={(params?.query ?? 1) + (params?.currentPage ?? "")} fallback={<div />}>
        <ComedianTable response={response} />
      </Suspense>
    </main>
  );
}
