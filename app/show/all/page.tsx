"use server";

import QueryableEntityTableContainer from "../../../components/container";
import { headers } from "next/headers";
import { show as queryMap } from "../../../database/sql";
import { getDB } from "../../../database";
import { EntityType } from "../../../objects/enum";
import { SearchParams } from "../../../objects/type/searchParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { Show } from "../../../objects/class/show/Show";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
const { db } = getDB();

export default async function ShowSearchResultsPage(props: {
    searchParams: Promise<SearchParams>;
}) {
    const paramsWrapper = await ParamsWrapper.fromServerSideParams(
        headers(),
        props.searchParams,
    );

    const queryHelper = new QueryHelper(queryMap, paramsWrapper);
    const response = await queryHelper.getAll<Show>(db.shows);

    const entityCollectionString = JSON.stringify(response.entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Show}
                totalEntities={response.total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
