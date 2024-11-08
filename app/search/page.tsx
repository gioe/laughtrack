import FilterPageContainer from "../../components/custom/filters/FilterPageContainer";
import { SearchParams } from "../../objects/interfaces/searchParams.interface";
import { getDB } from "../../database";
import { EntityType } from "../../util/enum";
const { db } = getDB();

export default async function SearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const queryParams = await props.searchParams;

    const results = await db.search.getSearchResults(
        EntityType.Show,
        queryParams,
    );

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer
                resultString={JSON.stringify(results)}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
