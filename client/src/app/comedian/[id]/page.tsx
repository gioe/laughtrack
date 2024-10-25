
import { executeGet } from "@/actions/executeGet";
import { EditComedianDropdown } from "@/components/custom/dropdown/EditComedianDropdown";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";
import { FilterParams } from "@/interfaces/filterParams.interface";
import { SortOptionInterface } from "@/interfaces/sortOption.interface";
import { PUBLIC_ROUTES } from "@/lib/routes";
import { Suspense } from "react";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import AddComedianTagModal from "@/components/custom/modals/AddComedianTagModal";
import EditSocialDataModal from "@/components/custom/modals/EditSocialDataModal";
import MergeComediansModal from "@/components/custom/modals/MergeComediansModal";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { TagInterface } from "@/interfaces/tag.interface";

export interface GetComedianDetailsParams extends FilterParams { }

const sortOptions: SortOptionInterface[] = [
  { name: 'Date', value: 'date' },
  { name: 'Most Popular', value: 'popularity' },
  { name: 'Price: Low to High', value: 'low_to_high' },
  { name: 'Price: High to Low', value: 'high_to_low' }
]

export async function getComedianDetailPageData(id: string, params: GetComedianDetailsParams) {

  const comedianDetailsUrl = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_DETAILS + `/${id}`
  const getAllComedianTags = process.env.URL_DOMAIN + PUBLIC_ROUTES.GET_COMEDIAN_TAGS

  return Promise.all([
    executeGet<PaginatedShowPageInterface>(comedianDetailsUrl, params),
    executeGet<TagInterface[]>(getAllComedianTags)]
    ).then((responses) => {
    return {
      paginatedData: responses[0],
      tags: responses[1],
    }
  })
}

export default async function ComedianDetailsPage(
  props: {
    params: Promise<{ id: string }>;
    searchParams: Promise<GetComedianDetailsParams>;
  }
) {
  const searchParams = await props.searchParams;
  const params = await props.params;

  const response = await getComedianDetailPageData(params.id, searchParams);
  const title = `${response.paginatedData.totalShows} upcoming shows`

  return (
    <div className="flex flex-col">
      <MergeComediansModal entity={response.paginatedData.entity} />
      <EditSocialDataModal entity={response.paginatedData.entity} />
      <AddComedianTagModal comedian={response.paginatedData.entity} tags={response.tags} />
      <section>
        <EntityBanner entity={response.paginatedData.entity} menu=
          {
            <EditComedianDropdown />
          }
        />
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

    </div>
  )
}
