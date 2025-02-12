import { Prisma } from "@prisma/client";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubByName } from "./findClubByName";
import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { getFilters } from "../../filters/getFilters";
import { SearchParamsHelper } from "@/objects/class/params/SearchParamsHelper";

export async function getClubDetailPageData(
    paramsHelper: SearchParamsHelper,
): Promise<ClubDetailResponse> {
    try {
        const providedFilters = paramsHelper.getParamValue(
            QueryProperty.Filters,
        ) as string;

        const helper = await QueryHelper.storePageParams(
            paramsHelper.asUrlSearchParams(),
            providedFilters == null ? undefined : providedFilters,
        );

        const [club, showsWithCount, filters] = await Promise.all([
            findClubByName(helper),
            findShowsWithCount({
                ...helper.asQueryFilters(),
                club: name,
            }),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ]);

        return {
            data: club,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        console.log(error);
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
