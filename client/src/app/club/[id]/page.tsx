
import { getClubDetails, GetClubDetailsParams, GetClubDetailsResponse } from "@/actions/clubs/getClubDetails";
import ClubBanner from "@/components/custom/banners/ClubBanner";
import ShowTable from "@/components/custom/tables/ShowTable";

export default async function ClubDetailPage({
  params,
}: {
  params: GetClubDetailsParams;
}) {

  const response = await getClubDetails(params);

  return (
    <div>
      <section>
        <ClubBanner
          club={response.entity}>
        </ClubBanner>
      </section>
      <section>
        <ShowTable response={response} />
      </section>
    </div>
  )
}
