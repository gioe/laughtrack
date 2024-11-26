/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { EntityType } from "../../../../../objects/enum";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { getDB } from "../../../../../database";
const { database } = getDB();

const getFilters = database.queries.getTags([EntityType.Comedian]);

export default async function ShowDetailPage(props: any) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        getFilters,
        props.params,
    );
    const { entity, total } = await database.page.getShowDetailPageData(
        helper.asQueryFilters(),
    );

    const containedEntitiesString = JSON.stringify(entity.containedEntities);
    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={total}
                entityCollectionString={containedEntitiesString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No comedians on this show
                    </h2>
                }
            />
        </section>
    );
}
