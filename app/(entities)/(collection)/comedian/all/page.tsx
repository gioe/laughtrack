/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../components/container";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../../../objects/enum";
import { getDB } from "../../../../../database";
const { database } = getDB();

const getFilters = database.queries.getTags([EntityType.Comedian]);

export default async function ComedianSearchPage(props: any) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        getFilters,
    );
    const { entities, total } = await database.page.getComedianSearchPageData(
        helper.asQueryFilters(),
    );
    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                totalEntities={total}
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
