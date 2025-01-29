import { findShowsWithCount } from "../../show/search/findShowsWithCount";
import { findComedianByName } from "./findComedianByName";
import { Prisma } from "@prisma/client";
import { ComedianDetailResponse } from "@/app/api/comedian/[name]/interface";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { DynamicRoute } from "@/objects/interface/identifable.interface";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";

export async function getComedianDetailPageData(
    searchParams: URLSearchParams,
    slug: DynamicRoute,
    headers: ReadonlyHeaders,
): Promise<ComedianDetailResponse> {
    try {
        const userId = headers.get("user_id");
        const { name } = slug;

        if (!name) {
            throw new Error("Defail request with no name should be impossible");
        }
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;
        const providedFilters = searchParams.get(QueryProperty.Filters);

        const helper = await QueryHelper.storePageParams(
            searchParams,
            providedFilters == null ? undefined : providedFilters,
            { name },
            normalizedUserId,
        );

        const [comedianData, showsWithCount, filters] = await Promise.all([
            findComedianByName(name, normalizedUserId),
            findShowsWithCount({
                ...helper.asQueryFilters(),
                comedian: name,
            }),
            getFilters(EntityType.Show, helper.asQueryFilters()),
        ]);

        return {
            data: comedianData,
            shows: showsWithCount.shows,
            total: showsWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
