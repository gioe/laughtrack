import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { getChainFilters } from "../../filters/getChainFilters";
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

        const [clubsWithCount, filters, chainFilters] = await Promise.all([
            findClubsWithCount(helper),
            getFilters(EntityType.Club, requestData.params.filters),
            getChainFilters(),
        ]);

        return {
            data: clubsWithCount.clubs,
            total: clubsWithCount.totalCount,
            filters,
            chainFilters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error("Database error in getSearchedClubs:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in getSearchedClubs:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while searching for clubs");
    }
}
