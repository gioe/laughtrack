import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { auth } from "@/auth";
import { unstable_cache } from "next/cache";
import Navbar from "@/ui/components/navbar";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FooterComponent from "@/ui/pages/home/footer";
import ClubDetailHeader from "@/ui/pages/entity/club/detailHeader";
import FilterBar from "@/ui/pages/search/filterBar";
import ComedianSearchBar from "@/ui/components/searchbar/comedian";
import FilterModal from "@/ui/components/modals/filter";
import { Session } from "next-auth";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const getCachedClubDetails = (currentSession: Session | null) =>
        unstable_cache(
            async () =>
                await makeRequest<ClubDetailResponse>(
                    APIRoutePath.Club + `/${paramsWrapper.asSlug()}`,
                    {
                        searchParams: paramsWrapper.asUrlSearchParams(),
                        revalidate: CACHE.detailPage,
                        session,
                    },
                ),
            ["comedian-detail-data", currentSession?.user?.id || ""],
            { revalidate: 86400 },
        );

    const { data, shows, total, filters } =
        await getCachedClubDetails(session)();

    return (
        <main className="min-h-screen w-full bg-ivory">
            <FilterModal filters={filters} total={total} />
            <Navbar currentUser={session?.user} />
            <ClubDetailHeader club={data} />
            <div className="max-w-7xl mx-auto p-6 flex flex-row">
                <TableWithHeader shows={shows} total={total}>
                    <FilterBar total={total} filters={filters.length > 0}>
                        <ComedianSearchBar />
                    </FilterBar>
                </TableWithHeader>
            </div>
            <FooterComponent />
        </main>
    );
}
