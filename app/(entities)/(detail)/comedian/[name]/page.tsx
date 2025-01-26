import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";
import { auth } from "@/auth";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/detailHeader";
import FooterComponent from "@/ui/pages/home/footer";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FilterBar from "@/ui/pages/search/filterBar";
import ClubSearchBar from "@/ui/components/searchbar/club";
import FilterModal from "@/ui/components/modals/filter";
import Navbar from "@/ui/components/navbar";

export default async function ComedianDetailsPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data, shows, total, filters } =
        await makeRequest<ComedianDetailResponse>(
            APIRoutePath.Comedian + `/${paramsWrapper.asSlug()}`,
            {
                searchParams: paramsWrapper.asUrlSearchParams(),
                revalidate: CACHE.detailPage,
            },
        );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <Navbar currentUser={session?.user} />
            <ComedianDetailHeader comedian={data} />
            <div className="max-w-7xl mx-auto p-6">
                <TableWithHeader shows={shows} total={total}>
                    <FilterBar total={total} filters={filters.length > 0}>
                        <ClubSearchBar />
                    </FilterBar>
                </TableWithHeader>
            </div>
            <FooterComponent />
        </main>
    );
}
