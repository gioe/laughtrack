import ClubTable from "../../../components/custom/tables/ClubTable";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { ClubInterface } from "../../../interfaces/club.interface";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { PUBLIC_ROUTES } from "../../../util/routes"
import { executePost } from '../../../actions/executePost';
import { SORT_OPTIONS } from '../../../util/sort';
import { Suspense } from 'react';
import { Paginated } from "../../../interfaces/paginated.interface";
import { generateUrl } from "../../../util/urlUtil";

interface AllClubsPageInteface extends Paginated {
  clubs: ClubInterface[]
}

async function getClubs(params?: SearchParams) {

  const getClubsUrl = generateUrl(PUBLIC_ROUTES.GET_ALL_CLUBS)

  return executePost<AllClubsPageInteface>(getClubsUrl, {
    query: params?.query ?? "",
    sort: params?.sort ?? "date",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10"
  })

}

export default async function AllClubsPage(
  props: {
    searchParams?: Promise<SearchParams>;
  }
) {

  const searchParams = await props.searchParams;
  const { clubs, totalResults } = await getClubs(searchParams);

  const title = `Browsing ${totalResults} clubs`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        itemCount={totalResults}
        sortOptions={SORT_OPTIONS.CLUB}
        child={
          <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
            <ClubTable clubs={clubs} />
          </Suspense>
        } />
    </main>
  );
}