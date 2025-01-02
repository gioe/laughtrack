/* eslint-disable @typescript-eslint/no-explicit-any */
import ShowCard from "../../../../../components/cards/show";
import QueryableEntityTableContainer from "../../../../../components/container";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { Show } from "../../../../../objects/class/show/Show";
import { RoutePath } from "../../../../../objects/enum";
import { Entity } from "../../../../../objects/interface";
import { executeGet } from "../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { ComedianDetailPageResponse } from "./interface";

export default async function ComedianDetailsPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ComedianDetail + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
        CACHE.detailPage,
    )) as ComedianDetailPageResponse;

    const renderFunction = (entity: Entity) => {
        return (
            <ShowCard
                key={`${entity.name}-${entity.id}`}
                show={entity as Show}
            />
        );
    };

    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={data.total}
                entityCollectionString={JSON.stringify(
                    data.entity.containedEntities,
                )}
                cardRenderFunction={renderFunction}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows for this comedian
                    </h2>
                }
            />
        </section>
    );
}
