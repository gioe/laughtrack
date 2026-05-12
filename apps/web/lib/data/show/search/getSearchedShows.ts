import { findShowsWithCount } from "./findShowsWithCount";
import { Prisma } from "@prisma/client";
import { getFilters } from "../../filters/getFilters";
import { EntityType } from "@/objects/enum";
import {
    FREE_FILTER_SLUG,
    QueryHelper,
} from "@/objects/class/query/QueryHelper";
import { ParameterizedRequestData } from "@/objects/interface";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { FilterDTO } from "@/objects/interface";
import { paramsContainsFilter } from "@/util/filter/util";

interface ShowSearchResponse {
    total: number;
    data: ShowDTO[];
    filters: FilterDTO[];
    zipCapTriggered: boolean;
}

// Synthetic Tag-style FilterDTO for the Free filter. No `tags` row backs it —
// see FREE_FILTER_SLUG. Negative id keeps it visibly distinct from real Tag
// IDs (Postgres serial starts at 1) so a downstream consumer that mistakes a
// FilterDTO for a Tag fails loudly instead of silently joining nothing.
const FREE_FILTER_ID = -1;
const FREE_FILTER_NAME = "Free";

export async function getSearchedShows(
    requestData: ParameterizedRequestData,
): Promise<ShowSearchResponse> {
    try {
        const helper = new QueryHelper(requestData);

        const [showsWithCount, tagFilters] = await Promise.all([
            findShowsWithCount(helper),
            getFilters(EntityType.Show, requestData.params.filters),
        ]);

        const freeFilter: FilterDTO = {
            id: FREE_FILTER_ID,
            slug: FREE_FILTER_SLUG,
            name: FREE_FILTER_NAME,
            selected: paramsContainsFilter(
                requestData.params.filters ?? null,
                FREE_FILTER_SLUG,
            ),
        };

        const filters = [freeFilter, ...tagFilters].sort((a, b) =>
            a.name.localeCompare(b.name),
        );

        return {
            total: showsWithCount.totalCount,
            data: showsWithCount.shows,
            filters,
            zipCapTriggered: showsWithCount.zipCapTriggered,
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
