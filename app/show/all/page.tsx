"use server";

import QueryableEntityTableContainer from "../../../components/container";
import { headers } from "next/headers";
import { EntityType } from "../../../objects/enum";
import { URLParams } from "../../../objects/type/urlParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ShowSearchPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storePageParams(props.searchParams, headers());

    const { entities, total } = await database.page.getShowSearchPageData();

    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Show}
                totalEntities={total}
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
