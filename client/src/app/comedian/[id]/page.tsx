
import { getComedianDetails } from "@/actions/getComedianDetails";
import ComedianBanner from "@/components/custom/banners/ComedianBanner";
import ShowFilters from "@/components/custom/filters/ShowFilters";
import { PaginationComponent } from "@/components/custom/Pagination";
import ShowTable from "@/components/custom/tables/ShowTable";
import { ComedianDetailsInterface, ComedianInterface } from "@/interfaces/comedian.interface";
import { LineupItemInterface, ShowDetailsInterface } from "@/interfaces/show.interface";

export default async function ComedianDetailsPage({ params }: { params: { id: string } }) {
  const { id } = params;

  const comedian = await getComedianDetails(id) as ComedianDetailsInterface;

  const filteredDates = comedian.dates.map((data: ShowDetailsInterface) => {
    return {
      ...data,
      lineup: data.lineup.filter((item: LineupItemInterface) => item.name !== comedian.name)
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
        <div className="flex flex-row bg-blue-600">
          <ShowFilters cities={[]}/>
          <PaginationComponent pageCount={10} /> 
        </div>
      </section>
      <section>
        <ShowTable shows={filteredDates} />
      </section>

    </div>
  )
}
