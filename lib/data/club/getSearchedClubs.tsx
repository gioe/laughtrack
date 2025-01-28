import { ClubSearchResponse } from "@/app/api/club/search/interface";
import { getClubCount } from "./getClubCount";
import { findClubs } from "./findClubs";
import { Prisma } from "@prisma/client";
import { getFilters } from "../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";

export async function getSearchedClubs(
    params: URLSearchParams,
    headers: ReadonlyHeaders,
    providedFilters?: string,
): Promise<ClubSearchResponse> {
    try {
        const userId = headers.get("user_id");
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;
        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters,
            undefined,
            normalizedUserId,
        );

        const [total, data, filters] = await Promise.all([
            getClubCount(helper.asQueryFilters()),
            findClubs(helper.asQueryFilters()),
            getFilters(EntityType.Club, helper.asQueryFilters()),
        ]);

        return {
            total,
            data,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
