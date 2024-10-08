
import { getClubDetails, GetClubDetailsParams } from "@/actions/clubs/getClubDetails";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";

export default async function ClubDetailPage({
  params,
}: {
  params: GetClubDetailsParams;
}) {

  const response = await getClubDetails(params) as PaginatedShowPageInterface;

  return (
    <div>
      <section>
        <EntityBanner entity={response.entity} />
      </section>
      <section>
        <ShowTable response={response} />
      </section>
    </div>
  )
}
