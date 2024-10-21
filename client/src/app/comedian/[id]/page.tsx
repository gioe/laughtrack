
import { getComedianDetails, GetComedianDetailsParams, GetComedianDetailsResponse } from "@/actions/comedians/getComedianDetails";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { EditComedianDropdown } from "@/components/custom/dropdown/EditComedianDropdown";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import AddShowModal from "@/components/custom/modals/AddShowModal";
import EditSocialDataModal from "@/components/custom/modals/EditSocialDataModal";
import MergeComediansModal from "@/components/custom/modals/MergeComediansModal";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";
import { Suspense } from "react";

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' },
  { name: 'Price: Low to High', value: 'low_to_high' },
  { name: 'Price: High to Low', value: 'high_to_low' }
]

export default async function ComedianDetailsPage({
  params,
  searchParams
}: {
  params: { id: string };
  searchParams: GetComedianDetailsParams;
}) {

  const response = await getComedianDetails(params.id, searchParams) as PaginatedShowPageInterface;
  const title = `${response.totalShows} upcoming shows`

  return (
    <div className="flex flex-col">
      <MergeComediansModal entity={response.entity} />
      <AddShowModal entity={response.entity} />
      <EditSocialDataModal entity={response.entity} />
      <section>
        <EntityBanner entity={response.entity} menu=
          {
            <EditComedianDropdown />
          }
        />
      </section>
      <section>
        <FilterPageContainer
          title={title}
          totalItems={response.totalShows}
          defaultSort={sortOptions[0].value}
          searchPlaceholder={'Search for comedian'}
          totalPages={response.totalPages}
          query={searchParams?.query}
          sortOptions={sortOptions}
          child={
            <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
              <ShowTable response={response} />
            </Suspense>
          } />
      </section>

    </div>
  )
}
