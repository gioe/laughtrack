import { getDB } from "../../../database";
import { getSortOptionsForEntityType } from "../../../util/sort";
import { EntityType } from "../../../util/enum";
import QueryableEntityTableContainer from "../../../components/container";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";
import { SearchParams } from "../../../objects/types/searchParams";

const { db } = getDB();

export default async function AllClubsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const paramsWrapper =
        LaughtrackSearchParams.asServerSideParams(searchParams);
    const response = await db.clubs.getAll(paramsWrapper);
    const responseString = JSON.stringify(response);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                sortOptions={getSortOptionsForEntityType(EntityType.Club)}
                responseString={responseString}
                defaultNode={<div></div>}
            />
        </main>
    );
}
