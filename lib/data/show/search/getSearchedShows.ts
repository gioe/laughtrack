import { findShowsWithCount } from "./findShowsWithCount"
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ParameterizedRequestData } from "@/objects/interface";

export async function getSearchedShows(requestData: ParameterizedRequestData) {
    try {
        const helper = new QueryHelper(requestData);

        const [showsWithCount, filters] = await Promise.all([
            findShowsWithCount(helper),
            getFilters(EntityType.Show, new URLSearchParams(requestData.params)),
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
