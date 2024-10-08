import { FetchComedianParams, getComedians, GetComediansResponse } from "@/actions/comedians/getComedians";
import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";

export default async function AllComediansPage({
  searchParams,
}: {
  searchParams?: FetchComedianParams;
}) {

  const response = await getComedians(searchParams) as GetComediansResponse

  return (
    <main className="flex-grow pt-5 bg-shark">
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ComedianTable response={response} query={searchParams?.query}/>
      </Suspense>
      <section>
      </section>
    </main>
  );
}
