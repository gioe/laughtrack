import { getShowCount } from "./getCount"
import { findShows } from "./findShows"
import { Prisma } from "@prisma/client";
import { getFilters } from "../filters/getFilters";
import { EntityType, QueryProperty } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ReadonlyHeaders } from "next/dist/server/web/spec-extension/adapters/headers";

export async function getSearchedShows(searchParams: URLSearchParams, headers: ReadonlyHeaders) {
    try {
        const userId = headers.get("user_id");
        const normalizedUserId =
            !userId || userId === "undefined" ? undefined : userId;
        const providedFilters = searchParams.get(QueryProperty.Filters)

        const helper = await QueryHelper.storePageParams(searchParams,
            providedFilters == null ? undefined : providedFilters,
            undefined,
            normalizedUserId);

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
