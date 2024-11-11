import { getSortOptionsForEntityType } from "../../../util/sort";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
import QueryableEntityTableContainer from "../../../components/container";
import { LaughtrackSearchParams } from "../../../objects/classes/searchParams/LaughtrackSearchParams";
import { SearchParams } from "../../../objects/types/searchParams";
const { db } = getDB();

export default async function AllComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const paramsWrapper =
        LaughtrackSearchParams.asServerSideParams(searchParams);
    const comedians = await db.comedians.getAll(paramsWrapper);
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
