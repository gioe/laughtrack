
import { Suspense } from "react";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { ShowInterface } from "../../../interfaces/show.interface";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { executeGet } from "../../../actions/executeGet";
import { TagInterface } from "../../../interfaces/tag.interface";
import ComedianTable from "../../../components/custom/tables/ComedianTable";
import EntityBanner from "../../../components/custom/banners/EntityBanner";
import AddComedianModal from "../../../components/custom/modals/AddComedianModal"
import useAddShowTagModal from "../../../hooks/useAddShowTagModal";
import useAddComedianModal from "../../../hooks/useAddComedianModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";

const menuItems = [
  { key: "tags", label: "Add Tags", store: useAddShowTagModal },
  { key: "comedian", label: "Add Comedian", store: useAddComedianModal },
]

interface ShowDetailPageInterface {
  show: ShowInterface;
  tags: TagInterface[]
}

async function getShowDetail(id: string, params: SearchParams): Promise<ShowDetailPageInterface> {
  const getShowDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_DETAILS + `/${id}`
  const getAllShowTags = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_SHOW_TAGS

  return Promise.all([
    executeGet<ShowInterface>(getShowDetailsUrl, params),
    executeGet<TagInterface[]>(getAllShowTags)]
  ).then((responses) => {
    return {
      show: responses[0],
      tags: responses[1],
    }
  })

}

export default async function ShowDetailPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { show, tags } = await getShowDetail(params.id, searchParams);

  return (
    <main className="flex-grow pt-5 bg-shark">
      <AddComedianModal show={show} intialComedians={show.lineup} />
      
      <TagEntityModal entity={show} type={Entity.Show} tags={tags} />
      <section>
        <EntityBanner entity={show} menuItems={menuItems} />
      </section>
      <section>
        <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
          <ComedianTable comedians={show.lineup} />
        </Suspense>
      </section>

    </main>
  )
}
