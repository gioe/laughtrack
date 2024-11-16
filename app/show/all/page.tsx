"use server";

import QueryableEntityTableContainer from "../../../components/container";
import { headers } from "next/headers";
import { EntityType } from "../../../objects/enum";
import { URLParams } from "../../../objects/type/urlParams";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { HeadersWrapper } from "../../../objects/class/headers/HeadersWrapper";
import { allShowPageMapper as mapper } from "./mapper";
import { AllShowPageData, AllShowPageDTO } from "./interface";

export default async function ShowSearchResultsPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);

    const { entities, total } = await QueryHelper.getPageData<
        AllShowPageDTO,
        AllShowPageData
    >(mapper);

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
