
import { getComedianDetails, GetComedianDetailsParams, GetComedianDetailsResponse } from "@/actions/comedians/getComedianDetails";
import ComedianBanner from "@/components/custom/banners/EntityBanner";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import EditSocialDataModal from "@/components/custom/modals/EditSocialDataModal";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";
import { Suspense } from "react";

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' }
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
      <EditSocialDataModal entity={response.entity} />
      <section>
        <ComedianBanner entity={response.entity} />
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
