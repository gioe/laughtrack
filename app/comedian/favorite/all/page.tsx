import QueryableEntityTableContainer from "../../../../components/container";
import { URLParams } from "../../../../objects/type/urlParams";
import { QueryHelper } from "../../../../objects/class/query/QueryHelper";
import { EntityType } from "../../../../objects/enum";
import { headers } from "next/headers";

export default async function FavoriteComediansPage(props: {
    searchParams: Promise<URLParams>;
}) {
    await QueryHelper.storeSearchParams(props.searchParams);
    await QueryHelper.storeHeaders(headers());

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
