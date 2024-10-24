
import ComedianTable from "@/components/custom/tables/ComedianTable";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { getShowDetails, GetShowDetailsParams, GetShowDetailsResponse } from "@/actions/shows/getShowDetails";
import { EditShowDropdown } from "@/components/custom/dropdown/EditShowDropdown";
import { Suspense } from "react";
import { getAllShowTags, GetAllShowTagsReponse } from "@/actions/shows/getAllShowTags";
import AddShowTagModal from "@/components/custom/modals/AddShowTagModal";
import AddComedianModal from "@/components/custom/modals/AddComedianModal";

export default async function ComedianDetailsPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<GetShowDetailsParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const response = await getShowDetails(params.id) as GetShowDetailsResponse;
  const showTagsResponse = await getAllShowTags() as GetAllShowTagsReponse

  return (
    <main className="flex-grow pt-5 bg-shark">
      <AddShowTagModal show={response.entity} tags={showTagsResponse.tags} />
      <AddComedianModal intialComedians={response.entity.lineup} show={response.entity}/>
      <section>
        <EntityBanner entity={response.entity} menu={<EditShowDropdown />} />
      </section>
      <section>
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ComedianTable response={{
            comedians: response.entity.lineup
          }} />
        </Suspense>
      </section>

    </main>
  )
}
