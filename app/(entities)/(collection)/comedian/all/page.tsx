/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import { auth } from "@/auth";
import FooterComponent from "@/ui/pages/home/footer";
import ComedianGrid from "@/ui/components/grid/comedian";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";

export default async function ComedianSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = await makeRequest<ComedianSearchResponse>(
        APIRoutePath.ComedianSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.search,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />
            <SearchDetailHeader
                title={`Search comedians`}
                subTitle={`${data.total} results`}
            />
            <FilterBar />
            <ComedianGrid contentString={JSON.stringify(data.entities)} />
            <FooterComponent />
        </main>
    );
}
