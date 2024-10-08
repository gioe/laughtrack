import { Suspense } from 'react';
import { getClubs, GetClubsParams, GetClubsResponse } from "@/actions/clubs/getClubs";
import ClubTable from "@/components/custom/tables/ClubTable";

export default async function AllClubsPage({
  searchParams,
}: {
  searchParams?: GetClubsParams;
}) {

  const response = await getClubs(searchParams) as GetClubsResponse

  return (
    <main className="flex-grow pt-5 bg-shark">
      <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
        <ClubTable response={response} query={searchParams?.query}/>
      </Suspense>
      <section>
      </section>
    </main>
  );
}
