import QueryableEntityTableContainer from "../../../components/container";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { URLParams } from "../../../objects/type/urlParams";
import { EntityType } from "../../../objects/enum";
import { headers } from "next/headers";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ComedianSearchPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storePageParams(props.searchParams, headers());

    const { entities, total } = await database.page.getComedianSearchPageData();

    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
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
