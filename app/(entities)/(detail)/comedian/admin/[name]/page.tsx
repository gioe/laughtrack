/* eslint-disable @typescript-eslint/no-explicit-any */
import EditComedianForm from "../../../../../../components/form/forms/comedian";
import { SearchParamsHelper } from "../../../../../../objects/class/params/SearchParamsHelper";
import { executeGet } from "../../../../../../util/actions/executeGet";
import { PUBLIC_ROUTES } from "../../../../../../util/routes";
import { ComedianDetailPageResponse } from "../../[name]/interface";

export default async function EditComedianPage(props: any) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        PUBLIC_ROUTES.COMEDIAN_DETAIL + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
    )) as ComedianDetailPageResponse;

    return (
        <section>
            <EditComedianForm comedianString={JSON.stringify(data.entity)} />
        </section>
    );
}
