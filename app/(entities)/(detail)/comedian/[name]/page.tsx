/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { PUBLIC_ROUTES } from "../../../../../util/routes";
import { ComedianDetailPageResponse } from "./interface";

export default async function ComedianDetailsPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        PUBLIC_ROUTES.COMEDIAN_DETAIL + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
        CACHE.detailPage,
    )) as ComedianDetailPageResponse;
    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={JSON.stringify(
                    data.entity.containedEntities,
                )}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows for this comedian
                    </h2>
                }
            />
        </section>
    );
}
