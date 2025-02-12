import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubsWithCount } from "./findClubsWithCount";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";

export async function getSearchedClubs(
    paramsHelper: SearchParamsHelper,
): Promise<ClubSearchResponse> {
    try {
        const providedFilters = paramsHelper.getParamValue(
            QueryProperty.Filters,
        ) as string;
        const helper = await QueryHelper.storePageParams(
            paramsHelper.asUrlSearchParams(),
            providedFilters == null ? undefined : providedFilters,
        );

        const [clubsWithCount, filters] = await Promise.all([
            findClubsWithCount(helper.asQueryFilters()),
            getFilters(EntityType.Club, helper.asQueryFilters()),
        ]);

        return {
            data: clubsWithCount.clubs,
            total: clubsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
