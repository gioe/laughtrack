/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../components/container";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ComedianSearchPage(props: any) {
    const filters = await QueryHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { entities, total } =
        await database.page.getComedianSearchPageData(filters);
    const tags = await database.queries.getTags(EntityType.Comedian);
    const tagsString = JSON.stringify(tags);
    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
                totalEntities={total}
                tagsString={tagsString}
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
