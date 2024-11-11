import { getSortOptionsForEntityType } from "../../../../util/sort";
import { EntityType } from "../../../../util/enum";
import { getDB } from "../../../../database";
import { getCurrentUser } from "../../../layout";
import QueryableEntityTableContainer from "../../../../components/container";
import { SearchParams } from "../../../../objects/types/searchParams";
import { LaughtrackSearchParams } from "../../../../objects/classes/searchParams/LaughtrackSearchParams";
const { db } = getDB();
export default async function FavoriteComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const user = await getCurrentUser();
    const searchParams = await props.searchParams;
    const paramsWrapper =
        LaughtrackSearchParams.asServerSideParams(searchParams);
    const comedians = await db.comedians.getAllFavorites(
        user?.id,
        paramsWrapper,
    );

    const sortOptions = getSortOptionsForEntityType(EntityType.Comedian);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                sortOptions={sortOptions}
                responseString={JSON.stringify(comedians)}
                defaultNode={<div></div>}
            />
        </main>
    );
}
