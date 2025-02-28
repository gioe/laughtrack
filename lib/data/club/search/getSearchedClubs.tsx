import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubsWithCount } from "./findClubsWithCount";
import { ParameterizedRequestData } from "@/objects/interface";
import { ClubSearchResponse } from "./interface";

export async function getSearchedClubs(
    requestData: ParameterizedRequestData,
): Promise<ClubSearchResponse> {
    try {
        const helper = new QueryHelper(requestData);

        const [clubsWithCount, filters] = await Promise.all([
            findClubsWithCount(helper),
            getFilters(
                EntityType.Club,
                new URLSearchParams(requestData.params),
            ),
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
