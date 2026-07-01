import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { getComedianHomeCityFilters } from "../../filters/getComedianHomeCityFilters";
import { getComedianHomeClubFilters } from "../../filters/getComedianHomeClubFilters";
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
        const [comediansWithCount, filters, homeCityFilters, homeClubFilters] =
            await Promise.all([
                findComediansWithCount(helper),
                getFilters(EntityType.Comedian, requestData.params.filters),
                getComedianHomeCityFilters(),
                getComedianHomeClubFilters(),
            ]);

        return {
            data: comediansWithCount.comedians,
            total: comediansWithCount.totalCount,
            filters,
            homeCityFilters,
            homeClubFilters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error("Database error in getSearchedComedians:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in getSearchedComedians:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while searching for comedians",
        );
    }
}
