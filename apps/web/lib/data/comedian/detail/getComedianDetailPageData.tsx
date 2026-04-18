import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { findComedianByName } from "./findComedianByName";
import { findPastShowsForComedian } from "./findPastShowsForComedian";
import { findRelatedComedians } from "./findRelatedComedians";
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

        const comedianData = await findComedianByName(helper);

        const [showsWithCount, pastShows, relatedComedians, filters] =
            await Promise.all([
                findShowsWithCount(helper),
                findPastShowsForComedian(helper),
                findRelatedComedians(comedianData.uuid),
                getFilters(EntityType.Show, requestData.params.filters),
            ]);

        return {
            data: comedianData,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            pastShows: pastShows.shows,
            pastShowsTotal: pastShows.totalCount,
            relatedComedians,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
