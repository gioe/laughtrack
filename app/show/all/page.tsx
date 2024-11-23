/* eslint-disable @typescript-eslint/no-explicit-any */
"use server";

import QueryableEntityTableContainer from "../../../components/container";
import { EntityType } from "../../../objects/enum";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ShowSearchPage(props: any) {
    const filters = await QueryHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { entities, total } =
        await database.page.getShowSearchPageData(filters);
    const tags = await database.queries.getTags(EntityType.Show);
    const tagsString = JSON.stringify(tags);
    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Show}
                totalEntities={total}
                entityCollectionString={entityCollectionString}
                tagsString={tagsString}
                defaultNode={
                    <h2 className="font-bold text-5xl w-maxtext-white pt-6">
                        No upcoming shows. Check back later.
                    </h2>
                }
            />
        </main>
    );
}
