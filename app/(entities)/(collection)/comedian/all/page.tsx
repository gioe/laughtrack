/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { executeGet } from "../../../../../util/actions/executeGet";
import { PUBLIC_ROUTES } from "../../../../../util/routes";
import { ComedianSearchResponse } from "./interface";

export default async function ComedianSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        PUBLIC_ROUTES.COMEDIAN_SEARCH,
        paramsWrapper.asUrlSearchParams(),
    )) as ComedianSearchResponse;

    const entityCollectionString = JSON.stringify(data.entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No comedians found. Who knows why.
                    </h2>
                }
            />
        </main>
    );
}
