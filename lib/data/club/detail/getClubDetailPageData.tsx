import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findClubByName } from "./findClubByName";
import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { getFilters } from "../../filters/getFilters";
import { ParameterizedRequestData } from "@/objects/interface";
import { ClubDetailResponse } from "./interface";

export async function getClubDetailPageData(
    requestData: ParameterizedRequestData,
): Promise<ClubDetailResponse> {
    try {
        const helper = new QueryHelper(requestData);

        const [club, showsWithCount, filters] = await Promise.all([
            findClubByName(helper),
            findShowsWithCount(helper),
            getFilters(
                EntityType.Show,
                new URLSearchParams(requestData.params),
            ),
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
