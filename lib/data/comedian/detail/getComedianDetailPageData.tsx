import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { findComedianByName } from "./findComedianByName";
import { Prisma } from "@prisma/client";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";

export async function getComedianDetailPageData(
    paramsHelper: SearchParamsHelper,
): Promise<ComedianDetailResponse> {
    try {
        const providedFilters = paramsHelper.getParamValue(
            QueryProperty.Filters,
        ) as string;

        const helper = await QueryHelper.storePageParams(
            paramsHelper.asUrlSearchParams(),
            providedFilters == null ? undefined : providedFilters,
        );

        const [comedianData, showsWithCount, filters] = await Promise.all([
            findComedianByName(helper),
            findShowsWithCount({
                ...helper.asQueryFilters(),
                comedian: name,
            }),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ]);

        return {
            data: comedianData,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
