import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ClubDetailPageResponse } from "@/app/api/club/[name]/interface";
import Navbar from "@/ui/components/navbar";
import { auth } from "@/auth";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import FooterComponent from "@/ui/pages/home/footer";
import ClubDetailHeader from "@/ui/pages/entity/club/detailHeader";
import ClubDataColumn from "@/ui/pages/entity/club/socialColumn";

export default async function ClubDetailPage(props: {
    searchParams: Promise<URLSearchParams>;
    params: Promise<DynamicRoute> | undefined;
}) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = await makeRequest<ClubDetailPageResponse>(
        APIRoutePath.Club + `/${paramsWrapper.asSlug()}`,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.detailPage,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <Navbar currentUser={session?.user} />
            <ClubDetailHeader clubString={JSON.stringify(data.entity)} />
            <div className="max-w-6xl mx-auto p-6 flex">
                <TableWithHeader
                    entityString={JSON.stringify(data.entity.containedEntities)}
                />
                <ClubDataColumn
                    telephoneNumber={"12122543480"}
                    website={data.entity.website}
                />
            </div>
            <FooterComponent />
        </main>
    );
}
