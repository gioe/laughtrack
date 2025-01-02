/* eslint-disable @typescript-eslint/no-explicit-any */
import ComedianCarouselCard from "../../../../../components/cards/carousel/comedian";
import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../objects/enum";
import { Entity } from "../../../../../objects/interface";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { ComedianSearchResponse } from "./interface";

export default async function ComedianSearchPage(props: any) {
    const paramsWrapper = await SearchParamsHelper.storePageParams(
        props.searchParams,
    );

    const { data } = (await executeGet(
        RoutePath.ComedianSearch,
        paramsWrapper.asUrlSearchParams(),
        CACHE.search,
    )) as ComedianSearchResponse;

    const entityCollectionString = JSON.stringify(data.entities);

    const renderFunction = (entity: Entity) => {
        return (
            <ComedianCarouselCard
                key={entity.name}
                entity={JSON.stringify(entity)}
            />
        );
    };

    return (
        <main className="flex-grow pt-5 bg-ivory">
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={entityCollectionString}
                cardRenderFunction={renderFunction}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No comedians found. Who knows why.
                    </h2>
                }
            />
        </main>
    );
}
