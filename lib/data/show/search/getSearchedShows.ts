import { findShowsWithCount } from "./findShowsWithCount"
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

export async function getSearchedShows(paramsString: string) {
    try {

        const helper = await QueryHelper.storePageParams(new URLSearchParams(paramsString))

        const [showsWithCount, filters] = await Promise.all([
            findShowsWithCount(helper),
            getFilters(EntityType.Show, helper),
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
