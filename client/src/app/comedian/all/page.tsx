import { getComedians, GetComediansResponse } from "@/actions/getComedians";
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
    <main className="flex-grow pt-14 m-5 px-6 bg-shark">
      <section>
        <ComedianTable comedians={response.comedians} />
      </section>
    </main>
  );
}
