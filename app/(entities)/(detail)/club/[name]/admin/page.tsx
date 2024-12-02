import { SearchParamsHelper } from "../../../../../../objects/class/params/SearchParamsHelper";
import { RoutePath } from "../../../../../../objects/enum";
import { executeGet } from "../../../../../../util/actions/executeGet";
import EditClubPageBody from "./body";
import { EditClubPageResponse } from "./interface";

export default async function EditClubPage(props) {
    const paramsHelper = await SearchParamsHelper.storePageParams(
        props.searchParams,
        props.params,
    );

    const { data } = (await executeGet(
        RoutePath.ClubDetail + `/${paramsHelper.asSlug()}` + "/admin",
        paramsHelper.asUrlSearchParams(),
    )) as EditClubPageResponse;

    return (
        <section>
            <EditClubPageBody clubString={JSON.stringify(data)} />
        </section>
    );
}
