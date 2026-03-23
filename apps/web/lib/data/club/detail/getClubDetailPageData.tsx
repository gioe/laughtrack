import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubByName } from "./findClubByName";
import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { getFilters } from "../../filters/getFilters";
import { ParameterizedRequestData } from "@/objects/interface";
import { ClubDetailResponse } from "./interface";
import { ClosedClubError } from "@/objects/ClosedClubError";
import { NotFoundError } from "@/objects/NotFoundError";

export async function getClubDetailPageData(
    requestData: ParameterizedRequestData,
): Promise<ClubDetailResponse> {
    try {
        const helper = new QueryHelper(requestData);
        helper.setClubName();

        const [club, showsWithCount, filters] = await Promise.all([
            findClubByName(helper),
            findShowsWithCount(helper),
            getFilters(EntityType.Show, requestData.params.filters),
        ]);
        return {
            data: club,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (
            error instanceof ClosedClubError ||
            error instanceof NotFoundError
        ) {
            throw error;
        }
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error("Database error in getClubDetailPageData:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in getClubDetailPageData:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while fetching club detail page data",
        );
    }
}
