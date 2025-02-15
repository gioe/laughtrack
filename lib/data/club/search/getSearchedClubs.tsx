import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubsWithCount } from "./findClubsWithCount";
import { ParameterizedRequestData } from "@/objects/interface";

export async function getSearchedClubs(
    requestData: ParameterizedRequestData,
): Promise<ClubSearchResponse> {
    try {
        const helper = await QueryHelper.storePageParams(
            new URLSearchParams(requestData.params),
        );

        const [clubsWithCount, filters] = await Promise.all([
            findClubsWithCount(helper),
            getFilters(EntityType.Club, helper),
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
