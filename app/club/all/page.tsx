import { getDB } from "../../../database";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { getSortOptionsForEntityType } from "../../../util/sort";
import { EntityType } from "../../../util/enum";
import QueryableTableContainer from "../../../components/container";

const { db } = getDB();

export default async function AllClubsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const clubs = await db.clubs.getAll(searchParams);
    const sortOptions = getSortOptionsForEntityType(EntityType.Club);
    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableTableContainer
                sortOptions={sortOptions}
                resultString={JSON.stringify(clubs)}
                defaultNode={<div></div>}
            />
        </main>
    );
}
