
import { getClubDetails } from "@/actions/getClubDetails";
import ClubBanner from "@/components/custom/banners/ClubBanner";
import ShowTable from "@/components/custom/tables/ShowTable";
import { ClubInterface } from "@/interfaces/club.interface";

export default async function ClubDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const response = await getClubDetails(id) as ClubInterface;

  return (
    <div>
      <section>
        <ClubBanner
          club={response}>
        </ClubBanner>
      </section>
      <section>
        <ShowTable shows={response.shows ?? []} />
      </section>
    </div>
  )
}
