
import ComedianTable from "@/components/custom/tables/ComedianTable";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { getShowDetails, GetShowDetailsParams, GetShowDetailsResponse } from "@/actions/shows/getShowDetails";
import { EditShowDropdown } from "@/components/custom/dropdown/EditShowDropdown";
import { Suspense } from "react";
import { getAllComedianFilters, GetAllComedianFiltersResponse } from "@/actions/comedians/getAllComedians";
import { getAllShowTags, GetAllShowTagsReponse } from "@/actions/shows/getAllShowTags";
import AddShowTagModal from "@/components/custom/modals/AddShowTagModal";
import AddComedianModal from "@/components/custom/modals/AddComedianModal";

export default async function ComedianDetailsPage({
  params,
  searchParams
}: {
  params: { id: string };
  searchParams: GetShowDetailsParams;
}) {

  const response = await getShowDetails(params.id, searchParams) as GetShowDetailsResponse;
  const filtersResponse = await getAllComedianFilters() as GetAllComedianFiltersResponse
  const showTagsResponse = await getAllShowTags() as GetAllShowTagsReponse

  return (
    <main className="flex-grow pt-5 bg-shark">
      <AddShowTagModal show={response.entity} tags={showTagsResponse.tags} />
      <AddComedianModal comedians={response.entity.lineup} filters={filtersResponse.filters}/>
      <section>
        <EntityBanner entity={response.entity} menu={<EditShowDropdown />} />
      </section>
      <section>
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ComedianTable response={{
            comedians: response.entity.lineup,
            totalPages: 1,
          }} />
        </Suspense>
      </section>

    </main>
  )
}
