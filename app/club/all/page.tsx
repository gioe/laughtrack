/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../components/container";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
import { getDB } from "../../../database";
const { database } = getDB();

export default async function ClubSearchPage(props: any) {
    const helper = await QueryHelper.storePageParams(props.searchParams);

    const { entities, total } = await database.page.getClubSearchPageData(
        helper.asQueryFilters(),
    );

    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Club}
                totalEntities={total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No clubs found. Who knows why.
                    </h2>
                }
            />
        </main>
    );
}
