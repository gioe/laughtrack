
import { executeGet } from "../../../actions/executeGet";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { Suspense } from "react";
import { TagInterface } from "../../../interfaces/tag.interface";
import { SORT_OPTIONS } from "../../../util/sort";
import { ComedianInterface } from "../../../interfaces/comedian.interface";
import { Paginated } from "../../../interfaces/paginated.interface";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import EditSocialDataModal from "../../../components/custom/modals/EditSocialDataModal";
import MergeComediansModal from "../../../components/custom/modals/MergeComediansModal";
import EntityBanner from "../../../components/custom/banners/EntityBanner";
import ShowTable from "../../../components/custom/tables/ShowTable";
import useSocialDataModal from "../../../hooks/useSocialDataModal";
import useMergeComediansModal from "../../../hooks/useMergeComediansModal";
import useAddComedianTagModal from "../../../hooks/useAddComedianTagModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { generateUrl } from "../../../util/urlUtil";

const menuItems = [
  { key: "social", label: "Edit Social Data", store: useSocialDataModal },
  { key: "merge", label: "Merge Comedians", store: useMergeComediansModal },
  { key: "tags", label: "Add Tags", store: useAddComedianTagModal }
]

interface ComedianDetailPageInterface extends Paginated {
  comedian: ComedianInterface;
  tags: TagInterface[];
}

async function getComedianDetail(id: string, params: SearchParams): Promise<ComedianDetailPageInterface> {

  const comedianDetailsUrl = generateUrl(PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${id}`)
  const getAllComedianTags = generateUrl(PUBLIC_ROUTES.GET_COMEDIAN_TAGS)

  return Promise.all([
    executeGet<any>(comedianDetailsUrl, params),
    executeGet<TagInterface[]>(getAllComedianTags)]
  ).then((responses) => {
    return {
      ...responses[0],
      tags: responses[1],
    } as ComedianDetailPageInterface
  });
}

export default async function ComedianDetailsPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { totalResults, comedian, tags } = await getComedianDetail(params.id, searchParams);
  const title = `${totalResults} upcoming shows`

  return (
    <div className="flex flex-col">
      <MergeComediansModal comedian={comedian} />
      <EditSocialDataModal comedian={comedian} />
      
      <TagEntityModal entity={comedian} type={Entity.Comedian} tags={tags} />
      <section>
        <EntityBanner entity={comedian} menuItems={menuItems}
        />
      </section>
      <section>
        <FilterPageContainer
          title={title}
          itemCount={totalResults}
          sortOptions={SORT_OPTIONS.SHOW}
          child={
            <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
              <ShowTable shows={comedian.dates} />
            </Suspense>
          } />
      </section>

    </div>
  )
}
