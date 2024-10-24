import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";
import { FetchFavoriteComedianParams, getFavoriteComedians } from "@/actions/comedians/getFavoriteComedians";

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
