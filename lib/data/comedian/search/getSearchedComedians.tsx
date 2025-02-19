import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { findComediansWithCount } from "./findComediansWithCount";
import { ParameterizedRequestData } from "@/objects/interface";
import { ComedianSearchResponse } from "./interface";

export async function getSearchedComedians(
    requestData: ParameterizedRequestData,
): Promise<ComedianSearchResponse> {
    const helper = new QueryHelper(requestData);

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
