import { getComedians, GetComediansResponse } from "@/actions/getComedians";
import { PaginationComponent } from "@/components/custom/Pagination";
import ComedianTable from "@/components/custom/tables/ComedianTable";

export default async function AllComediansPage({
    searchParams,
  }: {
    searchParams?: {
      page?: string;
    };
  }) {
    const currentPage = searchParams?.page || '1';

    const response = await getComedians(currentPage) as GetComediansResponse
    
    const pageCount = response.totalPages

    return (
        <div>
            <main className="flex">
                <section className="pt-14 px-6 pb-14">
                    <ComedianTable comedians={response.comedians} />
                </section>
                <section>
                <PaginationComponent pageCount={pageCount} />
                </section>
            </main>
        </div>
    );
  }
