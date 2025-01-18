import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import Navbar from "@/ui/components/navbar";
import { auth } from "@/auth";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FooterComponent from "@/ui/pages/home/footer";
import ClubDetailHeader from "@/ui/pages/entity/club/detailHeader";
import ClubDataColumn from "@/ui/pages/entity/club/socialColumn";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data, shows, total } = await makeRequest<ClubDetailResponse>(
        APIRoutePath.Club + `/${paramsWrapper.asSlug()}`,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.detailPage,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />
            <ClubDetailHeader club={data} />
            <div className="max-w-7xl mx-auto p-6 flex flex-row">
                <TableWithHeader shows={shows} total={total} />
                <ClubDataColumn club={data} />
            </div>
            <FooterComponent />
        </main>
    );
}
