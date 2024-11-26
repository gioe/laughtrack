/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../../../objects/enum";
import { getDB } from "../../../../../database";
const { database } = getDB();

const getFilters = database.queries.getTags([EntityType.Show]);

export default async function ComedianDetailsPage(props: any) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        getFilters,
        props.params,
    );

    const { entity, total } = await database.page.getComedianDetailPageData(
        helper.asQueryFilters(),
    );
    const entityString = JSON.stringify(entity);
    const containedEntitiesString = JSON.stringify(entity.containedEntities);

    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={total}
                entityCollectionString={containedEntitiesString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows for this comedian
                    </h2>
                }
            />
        </section>
    );
}
