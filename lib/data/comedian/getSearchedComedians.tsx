import { getComedianCount } from "./getComedianCount";
import { findComedians } from "./findComedians";
import { Prisma } from "@prisma/client";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

export async function getSearchedComedians(
    searchParams: URLSearchParams,
    providedFilters?: string,
): Promise<ComedianSearchResponse> {
    const helper = await QueryHelper.storePageParams(
        searchParams,
        providedFilters,
    );

    try {
        const [total, data, filters] = await Promise.all([
            getComedianCount(helper.asQueryFilters()),
            findComedians(helper.asQueryFilters()),
            getFilters(EntityType.Comedian, helper.asQueryFilters()),
        ]);

        return {
            data,
            total,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
