import QueryableEntityTableContainer from "../../../../components/container";
import { getDB } from "../../../../database";
import { getCurrentUser } from "../../../layout";
import { SearchParams } from "../../../../objects/type/searchParams";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../../objects/enum";
const { db } = getDB();

export default async function FavoriteComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const user = await getCurrentUser();
    const searchParams = await props.searchParams;
    const paramsWrapper = QueryHelper.asServerSideParams(searchParams);
    const response = await db.comedians.getAllFavorites(
        user?.id,
        paramsWrapper,
    );
    const entityCollectionString = JSON.stringify(response.entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
                totalEntities={response.total}
                entityCollectionString={entityCollectionString}
                defaultNode={<div></div>}
            />
        </main>
    );
}
