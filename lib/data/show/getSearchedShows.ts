import { getShowCount } from "./getCount"
import { findShows } from "./findShows"
import { Prisma } from "@prisma/client";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

export async function getSearchedShows(params: URLSearchParams, providedFilters?: string) {
    try {

        const helper = await QueryHelper.storePageParams(params, providedFilters);

        const [total, data, filters] = await Promise.all([
            getShowCount(helper.asQueryFilters()),
            findShows(helper.asQueryFilters()),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ])

        return {
            total,
            data,
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
