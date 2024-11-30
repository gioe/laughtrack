/* eslint-disable @typescript-eslint/no-empty-function */
import EditSocialDataForm from "../../../../../../components/form/forms/socialData";
import { SearchParamsHelper } from "../../../../../../objects/class/params/SearchParamsHelper";
import { executeGet } from "../../../../../../util/actions/executeGet";
import { CACHE } from "../../../../../../util/constants/cacheConstants";
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
        CACHE.detailPage,
    )) as ComedianDetailPageResponse;
    console.log(data);
    return (
        <section>
            <EditSocialDataForm name={""} onSubmit={() => {}} />
        </section>
    );
}
