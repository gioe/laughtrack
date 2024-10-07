import { FetchComedianParams, getComedians, GetComediansResponse } from "@/actions/comedians/getComedians";
import { Suspense } from 'react';
import ComedianTable from "@/components/custom/tables/ComedianTable";

export default async function AllComediansPage({
  params,
}: {
  params?: FetchComedianParams;
}) {

  const response = await getComedians(params) as GetComediansResponse

  return (
    <main className="flex-grow pt-14 m-5 px-6 bg-shark">
      <Suspense key={(params?.query ?? 1) + (params?.currentPage ?? "")} fallback={<div />}>
        <ComedianTable response={response} />
      </Suspense>
      <section>
      </section>
    </main>
  );
}
