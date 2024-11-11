"use server";

import QueryableTableContainer from "../../components/container";
import { getDB } from "../../database";
import { EntityType } from "../../util/enum";
import { getSortOptionsForEntityType } from "../../util/sort";
import { LaughtrackSearchParams } from "../../objects/classes/searchParams/LaughtrackSearchParams";
const { db } = getDB();

export type SearchParams = Record<string, string | string[] | undefined>;

export default async function SearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const queryParams = await props.searchParams;
    const params = LaughtrackSearchParams.asServerSideParams(queryParams);
    const results = await db.shows.getAll(params);
    const sortOptions = getSortOptionsForEntityType(EntityType.Show);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableTableContainer
                sortOptions={sortOptions}
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
