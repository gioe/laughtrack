import QueryableEntityTableContainer from "../../../../../components/container";
import { executeGet } from "../../../../../util/actions/executeGet";
import { ClubDetailPageResponse } from "./interface";
import { SearchParamsHelper } from "../../../../../objects/class/params/SearchParamsHelper";
import { CACHE } from "../../../../../util/constants/cacheConstants";
import { RoutePath } from "../../../../../objects/enum";
import { Entity } from "../../../../../objects/interface";
import ShowCard from "../../../../../components/cards/show";
import { Show } from "../../../../../objects/class/show/Show";

export default async function ClubDetailPage(props) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ClubDetail + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
        CACHE.detailPage,
    )) as ClubDetailPageResponse;

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
                        No shows for this club
                    </h2>
                }
            />
        </section>
    );
}
