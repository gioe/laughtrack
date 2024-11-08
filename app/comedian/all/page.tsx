import FilterPageContainer from "../../../components/custom/filters/FilterPageContainer";
import { SearchParams } from "../../../objects/interfaces/searchParams.interface";
import { getSortOptionsForEntityType } from "../../../util/sort";
import { EntityType } from "../../../util/enum";
import { getDB } from "../../../database";
const { db } = getDB();

export default async function AllComediansPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const comedians = await db.comedians.getAll(searchParams);
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
