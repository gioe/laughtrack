import { getShowCount } from "../show/getCount";
import { findShows } from "../show/findShows";
import { findClubByName } from "./findClubByName";
import { Prisma } from "@prisma/client";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";

export async function getClubDetailPageData(
    params: any,
    headers: ReadonlyHeaders,
    slug: DynamicRoute,
    providedFilters?: string,
): Promise<ClubDetailResponse> {
    try {
        const { name } = slug;
        const userId = headers.get("user_id");
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;

        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters,
            { name },
            normalizedUserId,
        );

        const [club, total, dates, filters] = await Promise.all([
            findClubByName(name ?? ""),
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
