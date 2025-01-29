import { Prisma } from "@prisma/client";
import { ComedianSearchResponse } from "@/app/api/comedian/search/interface";
import { getFilters } from "../../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";
import { findComediansWithCount } from "./findComediansWithCount";

export async function getSearchedComedians(
    searchParams: URLSearchParams,
    headers: ReadonlyHeaders,
): Promise<ComedianSearchResponse> {
    const userId = headers.get("user_id");
    const normalizedUserId =
        !userId || userId === "undefined" ? undefined : userId;
    const providedFilters = searchParams.get(QueryProperty.Filters);
    const helper = await QueryHelper.storePageParams(
        searchParams,
        providedFilters == null ? undefined : providedFilters,
        undefined,
        normalizedUserId,
    );

    try {
        const [comediansWithCount, filters] = await Promise.all([
            findComediansWithCount(helper.asQueryFilters()),
            getFilters(EntityType.Comedian, helper.asQueryFilters()),
        ]);
        return {
            data: comediansWithCount.comedians,
            total: comediansWithCount.totalCount,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
