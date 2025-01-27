import { findShows } from "../show/findShows";
import { findComedianByName } from "./findComedianByName";
import { getShowCount } from "../show/getCount";
import { Prisma } from "@prisma/client";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

export async function getComedianDetailPageData(
    params: URLSearchParams,
    name: string,
    providedFilters?: string,
): Promise<ComedianDetailResponse> {
    try {
        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters,
            {
                name,
            },
        );

        const [comedianData, totalCount, shows, filters] = await Promise.all([
            findComedianByName(name),
            getShowCount({
                ...helper.asQueryFilters(),
                comedianName: name,
            }),
            findShows({
                ...helper.asQueryFilters(),
                comedianName: name,
            }),
            getFilters(EntityType.Comedian),
        ]);

        return {
            data: comedianData,
            shows,
            total: totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
