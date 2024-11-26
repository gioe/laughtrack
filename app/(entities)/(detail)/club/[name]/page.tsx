import { EntityType } from "../../../../../objects/enum";
import QueryableEntityTableContainer from "../../../../../components/container";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { getDB } from "../../../../../database";
const { database } = getDB();

const getFilters = database.queries.getTags([EntityType.Show]);

export default async function ClubDetailPage(props) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        getFilters,
        props.params,
    );
    const { entity, total } = await database.page.getClubDetailPageData(
        helper.asQueryFilters(),
    );
    const containedEntitiesString = JSON.stringify(entity.containedEntities);
    const entityString = JSON.stringify(entity);

    return (
        <section>
            <QueryableEntityTableContainer
                totalEntities={total}
                entityCollectionString={containedEntitiesString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No shows for this club
                    </h2>
                }
            />
        </section>
    );
}
