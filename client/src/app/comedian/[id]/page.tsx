
import { getComedianDetails } from "@/actions/getComedianDetails";
import ComedianBanner from "@/components/custom/banners/ComedianBanner";
import ShowTable from "@/components/custom/tables/ShowTable";
import { ComedianInterface } from "@/interfaces/comedian.interface";
import { LineupItem } from "@/interfaces/comedian.interface copy";
import { ShowInterface } from "@/interfaces/show.interface";

export default async function ComedianDetailsPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const comedian = await getComedianDetails(id) as ComedianInterface;

  const filteredDates = comedian.dates?.map((data: ShowInterface) => {
    
    return {
      ...data,
      lineup: data.lineup.filter((item: LineupItem) => item.name !== comedian.name)
    }
  })

  return (
    <div>
      <section>
        <ComedianBanner
          comedian={comedian}>
        </ComedianBanner>
      </section>
      <section>
        <ShowTable shows={filteredDates ?? []} />
      </section>

    </div>
  )
}
