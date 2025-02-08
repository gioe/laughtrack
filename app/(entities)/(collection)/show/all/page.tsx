import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, EntityType, QueryProperty } from "@/objects/enum";
import { makeRequest } from "@/util/actions/makeRequest";
import { auth } from "@/auth";
import { ShowSearchResponse } from "@/app/api/show/search/interface";
import Navbar from "@/ui/components/navbar";
import FilterBar from "@/ui/pages/search/filterBar";
import ShowTable from "@/ui/pages/search/table";
import FooterComponent from "@/ui/pages/home/footer";
import SearchDetailHeader from "@/ui/pages/search/detailHeader";
import FilterModal from "@/ui/components/modals/filter";
import { CACHE } from "@/util/constants/cacheConstants";
import { SearchVariant } from "@/objects/enum/searchVariant";

export default async function ShowSearchPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );
    const { data, total, filters } = await makeRequest<ShowSearchResponse>(
        APIRoutePath.ShowSearch,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            session,
            next: {
                revalidate: CACHE.search,
                tags: ["show-search-data", session?.user?.id || ""],
            },
        },
    );

    console.log(data);

    const zip = paramsWrapper.getParamValue(QueryProperty.Zip);
    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <Navbar currentUser={session?.user} />
            <SearchDetailHeader
                title={`Search for shows near ${zip}`}
                subTitle={`${total} results`}
            />
            <FilterBar
                variant={SearchVariant.AllShows}
                total={total}
                filters={filters.length > 0}
            />
            <div className="mx-10">
                <ShowTable shows={data} />
            </div>
            <FooterComponent />
        </main>
    );
}
