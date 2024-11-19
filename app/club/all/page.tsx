import QueryableEntityTableContainer from "../../../components/container";
import { URLParams } from "../../../objects/type/urlParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../objects/enum";
import { headers } from "next/headers";
import { AllClubPageData, AllClubPageDTO } from "./interface";
import { allClubPageMapper as mapper } from "./mapper";

export default async function AllClubsPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storePageParams(props.searchParams, headers());

    const { entities, total } = await QueryHelper.getPageData<
        AllClubPageDTO,
        AllClubPageData
    >(mapper);

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
