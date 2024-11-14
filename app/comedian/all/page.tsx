import QueryableEntityTableContainer from "../../../components/container";
import { getDB } from "../../../database";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { SearchParams } from "../../../objects/type/searchParams";
import { EntityType } from "../../../objects/enum";
const { db } = getDB();

export default async function AllComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    const response = await db.comedians.getAll(paramsWrapper);
    const entityCollectionString = JSON.stringify(response.entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
                totalEntities={response.total}
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
