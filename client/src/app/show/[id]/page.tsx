
import ComedianTable from "@/components/custom/tables/ComedianTable";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { EditShowDropdown } from "@/components/custom/dropdown/EditShowDropdown";
import { Suspense } from "react";
import AddShowTagModal from "@/components/custom/modals/AddShowTagModal";
import AddComedianModal from "@/components/custom/modals/AddComedianModal";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { ShowInterface } from "@/interfaces/show.interface";
import { PUBLIC_ROUTES } from "@/lib/routes";
import { executeGet } from "@/actions/executeGet";
import { TagInterface } from "@/interfaces/tag.interface";

export interface GetShowDetailsParams extends FilterParams { }

export interface GetShowDetailsResponse {
  show: ShowInterface;
}

export async function getShowDetailPageData(id: string, params: GetShowDetailsParams) {
  const getShowDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_DETAILS + `/${id}`
  const getAllShowTags = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_TAGS

  return Promise.all([
    executeGet<GetShowDetailsResponse>(getShowDetailsUrl, params),
    executeGet<TagInterface[]>(getAllShowTags)]
    ).then((responses) => {
    return {
      paginatedData: responses[0],
      tags: responses[1],
    }
  })

}

export default async function ShowDetailPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<GetShowDetailsParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const response = await getShowDetailPageData(params.id, searchParams);

  return (
    <main className="flex-grow pt-5 bg-shark">
      <AddShowTagModal show={response.paginatedData.show} tags={response.tags} />
      <AddComedianModal intialComedians={response.paginatedData.show.lineup} show={response.paginatedData.show}/>
      <section>
        <EntityBanner entity={response.paginatedData.show} menu={<EditShowDropdown />} />
      </section>
      <section>
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ComedianTable response={{
            comedians: response.paginatedData.show
          }} />
        </Suspense>
      </section>

    </main>
  )
}
