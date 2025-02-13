import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findComediansWithCount } from "./findComediansWithCount";
import { PaginatedEntityResponseDTO } from "@/objects/interface";
import { ComedianDTO } from "@/objects/class/comedian/comedian.interface";

export type ComedianSearchResponse = PaginatedEntityResponseDTO<ComedianDTO>;

export async function getSearchedComedians(
    searchParams: string,
    userId?: string,
): Promise<ComedianSearchResponse> {
    const helper = await QueryHelper.storePageParams(
        new URLSearchParams(searchParams),
        userId,
    );

    try {
        const [comediansWithCount, filters] = await Promise.all([
            findComediansWithCount(helper),
            getFilters(EntityType.Comedian, helper),
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
