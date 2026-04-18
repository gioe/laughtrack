import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { findComedianByName } from "./findComedianByName";
import { findPastShowsForComedian } from "./findPastShowsForComedian";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ParameterizedRequestData } from "@/objects/interface";
import { ComedianDetailResponse } from "./interface";

export async function getComedianDetailPageData(
    requestData: ParameterizedRequestData,
): Promise<ComedianDetailResponse> {
    try {
        const helper = new QueryHelper(requestData);
        helper.setComedianName();
        const [comedianData, showsWithCount, pastShows, filters] =
            await Promise.all([
                findComedianByName(helper),
                findShowsWithCount(helper),
                findPastShowsForComedian(helper),
                getFilters(EntityType.Show, requestData.params.filters),
            ]);

        return {
            data: comedianData,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            pastShows: pastShows.shows,
            pastShowsTotal: pastShows.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
