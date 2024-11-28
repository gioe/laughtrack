/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { PUBLIC_ROUTES } from "../../../../../util/routes";
import { executeGet } from "../../../../../util/actions/executeGet";
import { ShowDetailPageResponse } from "./interface";

export default async function ShowDetailPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        PUBLIC_ROUTES.SHOW_DETAIL + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
    )) as ShowDetailPageResponse;

    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={JSON.stringify(
                    data.entity.containedEntities,
                )}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No comedians on this show
                    </h2>
                }
            />
        </section>
    );
}
