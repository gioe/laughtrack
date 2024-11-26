/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import QueryableEntityTableContainer from "../../../../../components/container";
import { EntityType } from "../../../../../objects/enum";
import { QueryHelper } from "../../../../../objects/class/query/QueryHelper";
import { getDB } from "../../../../../database";
const { database } = getDB();

const getFilters = database.queries.getTags([EntityType.Show]);

export default async function ShowSearchPage(props: any) {
    const helper = await QueryHelper.storePageParams(
        props.searchParams,
        getFilters,
    );

    const { entities, total } = await database.page.getShowSearchPageData(
        helper.asQueryFilters(),
    );
    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                totalEntities={total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
