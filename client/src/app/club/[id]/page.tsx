
import { getClubDetails, GetClubDetailsParams } from "@/actions/clubs/getClubDetails";
import EntityBanner from "@/components/custom/banners/EntityBanner";
import { EditClubDowndown } from "@/components/custom/dropdown/EditClubDropdown";
import FilterPageContainer from "@/components/custom/filters/FilterPageContainer";
import ClearShowsModal from "@/components/custom/modals/ClearShowsModal";
import ScrapeClubModal from "@/components/custom/modals/ScrapeClubModal";
import ShowTable, { PaginatedShowPageInterface } from "@/components/custom/tables/ShowTable";
import { Suspense } from "react";

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

  const response = await getClubDetails(params.id, searchParams) as PaginatedShowPageInterface;
  const title = `${response.totalShows} upcoming shows`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <ScrapeClubModal clubId={response.entity.id} />
      <ClearShowsModal clubId={response.entity.id} />
      <section>
        <EntityBanner entity={response.entity} menu={<EditClubDowndown />} />
      </section>
      <section>
        <FilterPageContainer
          title={title}
          itemCount={response.totalShows}
          defaultSort={sortOptions[0].value}
          searchPlaceholder={'Search for comedian'}
          query={searchParams?.query}
          sortOptions={sortOptions}
          child={
            <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
              <ShowTable response={response} />
            </Suspense>
          } />
      </section>
    </main>
  )
}
