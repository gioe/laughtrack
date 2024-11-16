import QueryableEntityTableContainer from "../../../../components/container";
import { URLParams } from "../../../../objects/type/urlParams";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../../objects/enum";
import { HeadersWrapper } from "../../../../objects/class/headers/HeadersWrapper";
import { headers } from "next/headers";
import { ParamsWrapper } from "../../../../objects/class/params/ParamsWrapper";

export default async function FavoriteComediansPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await HeadersWrapper.updateHeaders(headers());
    await ParamsWrapper.updateWithServerParams(props.searchParams);
    const response = await QueryHelper.getPageData();

    return (
        <main className="flex-grow pt-5 bg-shark">
            <QueryableEntityTableContainer
                entityType={EntityType.Comedian}
                totalEntities={1}
                entityCollectionString={""}
                defaultNode={<div></div>}
            />
        </main>
    );
}
