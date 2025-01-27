import { getShowCount } from "../show/getCount";
import { findShows } from "../show/findShows";
import { findClubByName } from "./findClubByName";
import { Prisma } from "@prisma/client";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";

export async function getClubDetailPageData(
    params: any,
    name: string,
    providedFilters?: string,
): Promise<ClubDetailResponse> {
    try {
        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters,
            { name },
        );

        const [club, total, dates, filters] = await Promise.all([
            findClubByName(name),
            getShowCount({ ...helper.asQueryFilters(), clubName: name }),
            findShows({ ...helper.asQueryFilters(), clubName: name }),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ]);

        return {
            data: club,
            shows: dates,
            total,
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
