import { SearchParams } from "../../../../objects/interfaces/searchParams.interface";
import FilterPageContainer from "../../../../components/custom/filters/FilterPageContainer";
import { getSortOptionsForEntityType } from "../../../../util/sort";
import { EntityType } from "../../../../util/enum";
import { getDB } from "../../../../database";
import { getCurrentUser } from "../../../layout";
const { db } = getDB();
export default async function FavoriteComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const user = await getCurrentUser();
    const searchParams = await props.searchParams;
    const comedians = await db.comedians.getAllFavorites(
        user?.id,
        searchParams,
    );

    const sortOptions = getSortOptionsForEntityType(EntityType.Comedian);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer
                sortOptions={sortOptions}
                resultString={JSON.stringify(comedians)}
                defaultNode={<div></div>}
            />
        </main>
    );
}
