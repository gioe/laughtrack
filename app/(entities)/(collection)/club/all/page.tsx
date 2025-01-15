/* eslint-disable @typescript-eslint/no-explicit-any */
import TableFilterBar from "@/ui/components/filter";
import ClubCarouselCard from "@/ui/components/grid/club/card/popular";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import FilterBar from "@/ui/pages/search/filterBar";
import FooterComponent from "@/ui/pages/home/footer";
import Navbar from "@/ui/components/navbar";
import { auth } from "@/auth";
import ClubGrid from "@/ui/components/grid/club";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";
import { StyleContextProvider } from "@/contexts/StyleProvider";

export default async function ClubSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = await makeRequest<ClubSearchResponse>(
        APIRoutePath.ClubSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.search,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>

            <SearchDetailHeader
                title={`Search clubs`}
                subTitle={`${data.total} results`}
            />
            <FilterBar />
            <ClubGrid contentString={JSON.stringify(data.entities)} />
            <FooterComponent />
        </main>
    );
}
