
import { ClubInterface } from "../../../interfaces/club.interface";
import { TagInterface } from "../../../interfaces/tag.interface";
import { Suspense } from "react";
import { Paginated } from "../../..//interfaces/paginated.interface";
import { executeGet } from "../../..//actions/executeGet";
import EntityBanner from "../../..//components/custom/banners/EntityBanner";
import FilterPageContainer from "../../..//components/custom/filters/FilterPageContainer";
import ClearShowsModal from "../../..//components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "../../..//components/custom/modals/ScrapeClubModal";
import ShowTable from "../../..//components/custom/tables/ShowTable";
import useAddClubTagModal from "../../..//hooks/useAddClubTagModal";
import useRunScrapeModal from "../../..//hooks/useRunScrapeModal";
import useClearShowsModal from "../../..//hooks/useClearShowsModal";
import TagEntityModal from "../../../components/custom/modals/TagEntityModal";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { SORT_OPTIONS } from "../../../util/sort";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { generateUrl } from "../../../util/urlUtil";

const menuItems = [
  { key: "tags", label: "Add Tags", store: useAddClubTagModal },
  { key: "scrape", label: "Run Scrape", store: useRunScrapeModal },
  { key: "clear", label: "Clear SHows", store: useClearShowsModal }
]

interface ClubDetailPageInterface extends Paginated {
  club: ClubInterface;
  tags: TagInterface[];
 }

async function getClubDetail(id: string, params: SearchParams): Promise<ClubDetailPageInterface> {

  const getClubDetailsUrl = generateUrl(PUBLIC_ROUTES.GET_CLUB_DETAILS + `/${id}`);
  const getAllClubsTags = generateUrl(PUBLIC_ROUTES.GET_CLUB_TAGS);

  return Promise.all(
    [executeGet<any>(getClubDetailsUrl, params), 
      executeGet<TagInterface[]>(getAllClubsTags)]
  ).then((responses) => {
    return {
      ...responses[0],
      tags: responses[1],
    }
  })
}

export default async function ClubDetailPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<SearchParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const { tags, club, totalResults } = await getClubDetail(params.id, searchParams)
  const title = `${totalResults} upcoming shows`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <ScrapeClubModal club={club} />
      <ClearShowsModal club={club} />
      
      <TagEntityModal entity={club} type={Entity.Club} tags={tags} />
      <section>
        <EntityBanner entity={club} menuItems={menuItems} />
      </section>
      <section>
        <FilterPageContainer
          title={title}
          itemCount={totalResults}
          sortOptions={SORT_OPTIONS.CLUB}
          child={
            <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
              <ShowTable shows={club.dates} />
            </Suspense>
          } />
      </section>
    </main>
  )
}
