import { findShowsWithCount } from "./findShowsWithCount"
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";

export async function getSearchedShows(paramsHelper: SearchParamsHelper) {
    try {

        const providedFilters = paramsHelper.getParamValue(
            QueryProperty.Filters,
        ) as string;

        const helper = await QueryHelper.storePageParams(paramsHelper.asUrlSearchParams(),
            providedFilters == null ? undefined : providedFilters);

        const [showsWithCount, filters] = await Promise.all([
            findShowsWithCount(helper.asQueryFilters()),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ])

        return {
            total: showsWithCount.totalCount,
            data: showsWithCount.shows,
            filters
        }
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }

}
