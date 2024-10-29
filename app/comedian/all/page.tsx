import { Suspense } from 'react';
import ComedianTable from "../../../components/custom/tables/ComedianTable";
import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { ComedianInterface } from "../../../interfaces/comedian.interface";
import { SearchParams } from "../../../interfaces/searchParams.interface";
import { PUBLIC_ROUTES } from "../../../util/routes";
import { executePost } from '../../../actions/executePost';
import { SORT_OPTIONS } from '../../../util/sort';
import { Paginated } from '../../../interfaces/paginated.interface';
import { generateUrl } from '../../../util/urlUtil';

interface AllComediansPageInterface extends Paginated {
  comedians: ComedianInterface[]
}

async function getComedians(params?: SearchParams) {
  
  const getComediansUrl = generateUrl(PUBLIC_ROUTES.GET_ALL_COMEDIANS)

  return executePost<AllComediansPageInterface>(getComediansUrl, {
    query: params?.query ?? "",
    sort: params?.sort ?? "popularity",
    page: params?.page ?? "0",
    rows: params?.rows ?? "10"
  })

}

export default async function AllComediansPage(
  props: {
    searchParams?: Promise<SearchParams>;
  }
) {
  const searchParams = await props.searchParams;
  const { comedians, totalResults } = await getComedians(searchParams)
  const title = `Browsing ${totalResults} comedians`

  return (
    <main className="flex-grow pt-5 bg-shark">
      <FilterPageContainer
        title={title}
        itemCount={totalResults}
        sortOptions={SORT_OPTIONS.COMEDIAN}
        child={
          <Suspense key={(searchParams?.query ?? 1) + (searchParams?.page ?? "")} fallback={<div />}>
            <ComedianTable comedians={comedians} />
          </Suspense>
        } />
    </main>
  );
}

