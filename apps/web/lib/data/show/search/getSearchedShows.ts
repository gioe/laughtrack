import { findShowsWithCount } from "./findShowsWithCount";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import { QueryHelper } from "@/objects/class/query/QueryHelper";
import { ParameterizedRequestData } from "@/objects/interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { FilterDTO } from "@/objects/interface";

interface ShowSearchResponse {
    total: number;
    data: ShowDTO[];
    filters: FilterDTO[];
}

export async function getSearchedShows(
    requestData: ParameterizedRequestData,
): Promise<ShowSearchResponse> {
    try {
        const helper = new QueryHelper(requestData);

        const [showsWithCount, filters] = await Promise.all([
            findShowsWithCount(helper),
            getFilters(EntityType.Show, requestData.params.filters),
        ]);

        return {
            total: showsWithCount.totalCount,
            data: showsWithCount.shows,
            filters,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error("Database error in getSearchedShows:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in getSearchedShows:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while searching for shows");
    }
}
