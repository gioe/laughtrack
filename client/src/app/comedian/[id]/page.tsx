
import { getComedianDetails } from "@/actions/getComedianDetails";
import ComedianBanner from "@/components/custom/ComedianBanner";
import ShowTable from "@/components/custom/ShowTable";
import { ComedianDetailsInterface, ComedianInterface } from "@/interfaces/comedian.interface";

export default async function ComedianDetailsPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const comedian = await getComedianDetails(id) as ComedianDetailsInterface;

  return (
    <div>
      <section>
        <ComedianBanner
          comedian={comedian}>
        </ComedianBanner>
      </section>
      <section>
        <ShowTable shows={comedian.shows} />
      </section>

    </div>
  )
}
