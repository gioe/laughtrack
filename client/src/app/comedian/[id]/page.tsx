
import { getComedianDetails, GetComedianDetailsParams, GetComedianDetailsResponse } from "@/actions/comedians/getComedianDetails";
import ComedianBanner from "@/components/custom/banners/EntityBanner";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";

export default async function ComedianDetailsPage({
  params,
}: {
  params: GetComedianDetailsParams;
}) {

  const response = await getComedianDetails(params) as PaginatedShowPageInterface;

  return (
    <div className="flex flex-col">
      <section>
        <ComedianBanner entity={response.entity} />
      </section>
      <section>
        <ShowTable response={response} />
      </section>

    </div>
  )
}
