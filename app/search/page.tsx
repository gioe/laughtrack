import FilterPageContainer from "../../components/custom/filters/FilterPageContainer";
import { SearchParams } from "../../objects/interfaces/searchParams.interface";
import { getDB } from "../../database";
import { EntityType } from "../../util/enum";
import { Show } from "../../objects/classes/show/Show";
import ShowInfoCard from "../../components/custom/tables/cards/ShowCard";
const { db } = getDB();

export default async function SearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const queryParams = await props.searchParams;

    const results = (await db.search.getSearchResults(
        EntityType.Show,
        queryParams,
    )) as Show[];

    console.log(results);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <FilterPageContainer<Show>
                suspenseKey={
                    (queryParams.query ?? "") + (queryParams.page ?? 0)
                }
                results={results}
                renderItem={(show) => {
                    return <ShowInfoCard show={show} />;
                }}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
