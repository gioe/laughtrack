import { getComedians, GetComediansResponse } from "@/actions/getComedians";
import ComedianTable from "@/components/custom/ComedianTable";
import { PaginationComponent } from "@/components/custom/Pagination";

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
