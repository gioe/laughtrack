import EditComedianForm from "../../../../../../components/form/forms/comedian";
import { SearchParamsHelper } from "../../../../../../objects/class/params/SearchParamsHelper";
import { executeGet } from "../../../../../../util/actions/executeGet";
import { PUBLIC_ROUTES } from "../../../../../../util/routes";
import { EditClubPageResponse } from "./interface";

export default async function EditClubPage(props) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        PUBLIC_ROUTES.EDIT_CLUB + `/${paramsHelper.asSlug()}`,
        paramsHelper.asUrlSearchParams(),
    )) as EditClubPageResponse;

    return (
        <section>
            <EditComedianForm comedianString={JSON.stringify(data)} />
        </section>
    );
}
