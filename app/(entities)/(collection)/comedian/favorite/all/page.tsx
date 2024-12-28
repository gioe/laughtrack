/* eslint-disable @typescript-eslint/no-explicit-any */
import QueryableEntityTableContainer from "../../../../../../components/container";
import { QueryHelper } from "../../../../../../objects/class/query/QueryHelper";

export default async function FavoriteComediansPage(props: any) {
    // const filters = await QueryHelper.storePageParams(
    //     props.searchParams,
    //     props.params,
    // );

    return (
        <main className="flex-grow pt-5 bg-ivory">
            <QueryableEntityTableContainer
                totalEntities={1}
                entityCollectionString={""}
                defaultNode={<div></div>}
            />
        </main>
    );
}
