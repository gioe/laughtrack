import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { findClubsWithCount } from "./findClubsWithCount";

export async function getSearchedClubs(
    params: URLSearchParams,
    headers: ReadonlyHeaders,
): Promise<ClubSearchResponse> {
    try {
        const userId = headers.get("user_id");
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;
        const providedFilters = params.get(QueryProperty.Filters);

        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters == null ? undefined : providedFilters,
            undefined,
            normalizedUserId,
        );

        const [clubsWithCount, filters] = await Promise.all([
            findClubsWithCount(helper.asQueryFilters()),
            getFilters(EntityType.Club, helper.asQueryFilters()),
        ]);

        return {
            data: clubsWithCount.clubs,
            total: clubsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
