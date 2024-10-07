import { GetComediansResponse } from "@/actions/fetchFilteredComedians";
import { PaginationComponent } from "@/components/custom/pagination/Pagination";
import { Suspense } from 'react';
import TextSearchBar from "@/components/custom/search/TextSearchBar";
import ComedianTable from "@/components/custom/tables/ComedianTable";
import { fetchFavoriteComedians } from "@/actions/fetchFavoriteComedians";

export default async function FavoriteComediansPage({
  searchParams,
}: {
  searchParams?: {
    query?: string;
    page?: string;
  };
}) {

  const query = searchParams?.query || '';
  const currentPage = searchParams?.page || '1';
  const response = await fetchFavoriteComedians(currentPage, query) as GetComediansResponse
  const pageCount = response.totalPages

  return (
    <main className="flex-grow pt-14 m-5 px-6 bg-shark">
      <div className="flex flex-row">
        <TextSearchBar query={query}/>
        <PaginationComponent pageCount={pageCount} />
      </div>
      <Suspense key={query + currentPage} fallback={<div />}>
        <ComedianTable comedians={response.comedians} />
      </Suspense>
      <section>
      </section>
    </main>
  );
}
