
import { getClubDetails } from "@/actions/getClubDetails";
import ClubBanner from "@/components/custom/banners/ClubBanner";
import ShowTable from "@/components/custom/tables/ShowTable";
import { ClubDetailsInterface } from "@/interfaces/club.interface";

export default async function ClubDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const clubDetails = await getClubDetails(id) as ClubDetailsInterface;

  return (
    <div>
      <section>
        <ClubBanner
          club={clubDetails}>
        </ClubBanner>
      </section>
      <section>
        <ShowTable shows={clubDetails.dates} />
      </section>
    </div>
  )
}
