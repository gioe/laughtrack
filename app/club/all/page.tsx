import { getDB } from "../../../database";
import QueryableEntityTableContainer from "../../../components/container";
import { SearchParams } from "../../../objects/type/searchParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";

const { db } = getDB();

export default async function AllClubsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    const response = await db.clubs.getAll(paramsWrapper);
    const entityCollectionString = JSON.stringify(response.entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Club}
                totalEntities={response.total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No clubs found. Who knows why.
                    </h2>
                }
            />
        </main>
    );
}
