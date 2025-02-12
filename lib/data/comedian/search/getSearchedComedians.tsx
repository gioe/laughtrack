import { Prisma } from "@prisma/client";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findComediansWithCount } from "./findComediansWithCount";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";

export async function getSearchedComedians(
    paramsHelper: SearchParamsHelper,
): Promise<ComedianSearchResponse> {
    const providedFilters = paramsHelper.getParamValue(
        QueryProperty.Filters,
    ) as string;

    const helper = await QueryHelper.storePageParams(
        paramsHelper.asUrlSearchParams(),
        providedFilters == null ? undefined : providedFilters,
    );

    try {
        const [comediansWithCount, filters] = await Promise.all([
            findComediansWithCount(helper.asQueryFilters()),
            getFilters(EntityType.Comedian, helper.asQueryFilters()),
        ]);
        return {
            data: comediansWithCount.comedians,
            total: comediansWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
