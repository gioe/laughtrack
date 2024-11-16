import QueryableEntityTableContainer from "../../../components/container";
import { QueryHelper } from "../../../objects/class/query/QueryHelper";
import { URLParams } from "../../../objects/type/urlParams";
import { EntityType } from "../../../objects/enum";
import { headers } from "next/headers";
import { HeadersWrapper } from "../../../objects/class/headers/HeadersWrapper";
import { ParamsWrapper } from "../../../objects/class/params/ParamsWrapper";
import { allComedianPaegDataMapper as mapper } from "./mapper";
import { AllComedianPageData, AllComedianPageDTO } from "./interface";
export default async function AllComediansPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);
    const { entities, total } = await QueryHelper.getPageData<
        AllComedianPageDTO,
        AllComedianPageData
    >(mapper);
    const entityCollectionString = JSON.stringify(entities);

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
                totalEntities={total}
                entityCollectionString={entityCollectionString}
                defaultNode={
                    <h2 className="font-bold text-5xl text-white pt-6">
                        No comedians found. Who knows why.
                    </h2>
                }
            />
        </main>
    );
}
