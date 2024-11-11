"use server";

import QueryableEntityTableContainer from "../../components/container";
import { getDB } from "../../database";
import { EntityType } from "../../util/enum";
import { getSortOptionsForEntityType } from "../../util/sort";
import { SearchParams } from "../../objects/types/searchParams";
import { LaughtrackSearchParams } from "../../objects/classes/searchParams/LaughtrackSearchParams";
const { db } = getDB();

export default async function SearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const searchParams = await props.searchParams;
    const paramsWrapper =
        LaughtrackSearchParams.asServerSideParams(searchParams);
    const response = await db.shows.getAll(paramsWrapper);
    const responseString = JSON.stringify(response);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                sortOptions={getSortOptionsForEntityType(EntityType.Show)}
                responseString={responseString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
