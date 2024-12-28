/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../objects/enum";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { ShowSearchResponse } from "./interface";

export default async function ShowSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        RoutePath.ShowSearch,
        paramsWrapper.asUrlSearchParams(),
        CACHE.search,
    )) as ShowSearchResponse;

    const entityCollectionString = JSON.stringify(data.entities);

    return (
        <main className="flex-grow pt-5 bg-ivory">
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
