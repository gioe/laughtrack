import TableFilterBar from "@/ui/components/filter";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";
import { APIRoutePath, StyleContextKey } from "@/objects/enum";
import { CACHE } from "@/util/constants/cacheConstants";
import { makeRequest } from "@/util/actions/makeRequest";
import { ComedianDetailPageResponse } from "@/app/api/comedian/[name]/interface";
import Navbar from "@/ui/components/navbar";
import { auth } from "@/auth";
import ComedianDetailHeader from "@/ui/pages/entity/comedian/detailHeader";
import FooterComponent from "@/ui/pages/home/footer";
import TableWithHeader from "@/ui/pages/entity/comedian/table";
import SocialMediaColumn from "@/ui/pages/entity/comedian/socialColumn";
import { StyleContextProvider } from "@/contexts/StyleProvider";

export default async function ComedianDetailsPage(props: any) {
    const session = await auth();

    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = await makeRequest<ComedianDetailPageResponse>(
        APIRoutePath.Comedian + `/${paramsWrapper.asSlug()}`,
        {
            searchParams: paramsWrapper.asUrlSearchParams(),
            revalidate: CACHE.detailPage,
        },
    );

    return (
        <main className="min-h-screen w-full bg-ivory">
            <StyleContextProvider initialContext={StyleContextKey.Search}>
                <Navbar currentUser={session?.user} />
            </StyleContextProvider>
            <ComedianDetailHeader
                favorite={data.entity.isFavorite}
                comedianId={data.entity.id}
                name={data.entity.name}
                images={[]}
            />
            <div className="max-w-6xl mx-auto p-6 flex">
                <TableWithHeader
                    entityString={JSON.stringify(data.entity.containedEntities)}
                />
                <SocialMediaColumn socialData={data.entity.socialData} />
            </div>
            <FooterComponent />
        </main>
    );
}
