/* eslint-disable @typescript-eslint/no-explicit-any */
import { SearchParamsHelper } from "../../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../../objects/enum";
import { executeGet } from "../../../../../../util/actions/executeGet";
import EditComedianPageBody from "./body";
import { EditComedianPageResponse } from "./interface";

export default async function EditComedianPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ComedianDetail + `/${paramsHelper.asSlug()}` + `/admin`,
        paramsHelper.asUrlSearchParams(),
    )) as EditComedianPageResponse;

    return (
        <section>
            <EditComedianPageBody comedianString={JSON.stringify(data)} />
        </section>
    );
}
