import { Prisma } from "@prisma/client";
import { ClubDetailResponse } from "@/app/api/club/[name]/interface";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { findClubByName } from "./findClubByName";
import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { getFilters } from "../../filters/getFilters";

export async function getClubDetailPageData(
    params: URLSearchParams,
    headers: ReadonlyHeaders,
    slug: DynamicRoute,
): Promise<ClubDetailResponse> {
    try {
        const { name } = slug;
        const userId = headers.get("user_id");
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;
        const providedFilters = params.get(QueryProperty.Filters);

        if (!name) {
            throw new Error(`Detail request with no name should be impossible`);
        }
        const helper = await QueryHelper.storePageParams(
            params,
            providedFilters == null ? undefined : providedFilters,
            undefined,
            normalizedUserId,
        );

        const [club, showsWithCount, filters] = await Promise.all([
            findClubByName(name),
            findShowsWithCount({
                ...helper.asQueryFilters(),
                club: name,
            }),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ]);

        return {
            data: club,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
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
