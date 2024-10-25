
import { executeGet } from "@/actions/executeGet";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { EditClubDowndown } from "@/components/custom/dropdown/EditClubDropdown";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import AddClubTagModal from "@/components/custom/modals/AddClubTagModal";
import ClearShowsModal from "@/components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "@/components/custom/modals/ScrapeClubModal";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";
import { ClubInterface } from "@/interfaces/club.interface";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { TagInterface } from "@/interfaces/tag.interface";
import { PUBLIC_ROUTES } from "@/lib/routes";
import { Suspense } from "react";

export interface GetClubDetailsParams extends FilterParams { }

export async function getClubDetailPageData(id: string, params: GetClubDetailsParams) {
  const getClubDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CLUB_DETAILS + `/${id}`
  const getAllClubsTags = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_CLUB_TAGS

  return Promise.all([
    executeGet<PaginatedShowPageInterface>(getClubDetailsUrl, params),
    executeGet<TagInterface[]>(getAllClubsTags)]
    ).then((responses) => {
    return {
      paginatedData: responses[0],
      clubTags: responses[1],
    }
  })

}

const sortOptions = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' },
  { name: 'Price: Low to High', value: 'low_to_high' },
  { name: 'Price: High to Low', value: 'high_to_low' }
]

export default async function ClubDetailPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<GetClubDetailsParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const response = await getClubDetailPageData(params.id, searchParams)
  const title = `${response.paginatedData.totalShows} upcoming shows`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <ScrapeClubModal clubId={response.paginatedData.entity.id} />
      <ClearShowsModal clubId={response.paginatedData.entity.id} />
      <AddClubTagModal club={response.paginatedData.entity as ClubInterface} tags={response.clubTags} />
      <section>
        <EntityBanner entity={response.paginatedData.entity} menu={<EditClubDowndown />} />
      </section>
      <section>
        <FilterPageContainer
          title={title}
          itemCount={response.paginatedData.totalShows}
          defaultSort={sortOptions[0].value}
          searchPlaceholder={'Search for comedian'}
          query={searchParams?.query}
          sortOptions={sortOptions}
          child={
            <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
              <ShowTable response={response.paginatedData} />
            </Suspense>
          } />
      </section>
    </main>
  )
}
