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
      <section className="flex-grow pt-5 px-6">
      <h1 className="text-3xl font-semibold mt-2 mb-6 text-silver-gray">{`${response.totalComedians} total comedians`}</h1>
      </section>
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ComedianTable response={response} query={searchParams?.query} />
      </Suspense>
      <section>
      </section>
    </main>
  );
}
