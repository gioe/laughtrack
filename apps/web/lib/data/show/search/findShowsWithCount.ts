import { db } from "@/lib/db";
import {
    AVAILABLE_SHOW_WHERE,
    buildShowSelect,
    mapShowRowToDTO,
    type PublicShowRow,
} from "@/lib/data/show/showSelect";
import { QueryHelper, SHOW_SORT_MAP } from "@/objects/class/query/QueryHelper";
import { SortParamValue } from "@/objects/enum/sortParamValue";
import { ShowDTO } from "@/objects/class/show/show.interface";
import { computeShowSoldOut } from "@/util/show/soldOutUtil";
import { Prisma } from "@prisma/client";

interface ShowsResponse {
    shows: ShowDTO[];
    totalCount: number;
    zipCapTriggered: boolean;
}

interface ClubShowsOptions {
    page?: string;
    size?: string;
    profileId?: string;
    userId?: string;
}

export async function findShowsWithCount(
    helper: QueryHelper,
): Promise<ShowsResponse> {
    try {
        const clubNameClause = helper.getClubNameClause();
        const clubId = helper.params.clubId
            ? Number(helper.params.clubId)
            : undefined;
        const zipCodeClause = helper.getZipCodeClause();
        // getDateClause returns {} when no fromDate/toDate are set. Show search
        // always wants upcoming-only results, so supply the default here.
        const dateClause = helper.getDateClause();
        const dateFilter =
            "date" in dateClause ? dateClause : { date: { gte: new Date() } };
        const searchWhereClause: Prisma.ShowWhereInput = {
            // Shows whose dates are Greater Than (gte) today's date or a date parameter, if provided
            ...dateFilter,

            // Club conditions
            club: {
                visible: true,
                ...(clubId !== undefined && { id: clubId }),
                // Only add these clauses if they have values
                ...(clubNameClause.name && clubNameClause),
                ...(zipCodeClause.zipCode && zipCodeClause),
            },

            // If the 'comedian' param is provided, it means we're doing a search for shows that contain a specific comedian.
            ...helper.getLineupItemClause(),

            // Match any shows with tags matching the display of the provided filter
            ...helper.getShowTagsClause(),
            ...helper.getShowTypeClause(),

            // Free filter: when the FREE_FILTER_SLUG is in the filters CSV,
            // narrow to shows with at least one ticket priced 0 or NULL.
            ...helper.getFreeShowsClause(),
        };
        const searchAndClauses = Array.isArray(searchWhereClause.AND)
            ? searchWhereClause.AND
            : searchWhereClause.AND
              ? [searchWhereClause.AND]
              : [];
        const whereClause: Prisma.ShowWhereInput = {
            ...searchWhereClause,
            AND: [...searchAndClauses, AVAILABLE_SHOW_WHERE],
        };

        // Sequential awaits instead of a RepeatableRead transaction — slight count/data
        // skew between the two calls is acceptable for paginated search (same pattern
        // as findComediansWithCount and findClubsWithCount). The transaction was
        // crashing on Neon serverless (digest 3246448085).
        const totalCount = await db.show.count({
            where: whereClause,
        });

        const filteredShows = await db.show.findMany({
            where: whereClause,
            select: buildShowSelect({
                includeDescription: true,
                favoriteComediansProfileId: helper.getProfileId(),
            }),
            ...helper.getGenericClauses(totalCount, SHOW_SORT_MAP, [
                { date: "asc" },
                { id: "asc" },
            ]),
        });
        const availableShows = filteredShows.filter(
            (show) => !computeShowSoldOut(show.name, show.tickets),
        );
        // distanceMiles is null whenever zip is absent (e.g. club detail page, comedian page).
        // Cards hide the distance label when distanceMiles is null — this is intentional.
        const searchedZip = helper.params.zip;
        return {
            zipCapTriggered: helper.isZipCapTriggered(),
            totalCount: Math.max(
                0,
                totalCount - (filteredShows.length - availableShows.length),
            ),
            shows: availableShows.map((show) =>
                mapSearchShowToDTO(show, helper, searchedZip),
            ),
        };
    } catch (error) {
        if (error instanceof Error) {
            console.error("Error in findShowsWithCount:", error);
            throw error;
        }
        throw new Error("An unknown error occurred while fetching shows");
    }
}

export async function findUpcomingShowsForClub(
    clubId: number,
    options: ClubShowsOptions = {},
): Promise<ShowsResponse> {
    const helper = new QueryHelper({
        params: {
            page: options.page,
            size: options.size,
            sort: SortParamValue.DateAsc,
        },
        timezone: "UTC",
        profileId: options.profileId,
        userId: options.userId,
    });
    const whereClause: Prisma.ShowWhereInput = {
        date: { gte: new Date() },
        club: {
            id: clubId,
            visible: true,
        },
        AND: [AVAILABLE_SHOW_WHERE],
    };

    const totalCount = await db.show.count({ where: whereClause });
    const filteredShows = await db.show.findMany({
        where: whereClause,
        select: buildShowSelect({
            includeDescription: true,
            favoriteComediansProfileId: helper.getProfileId(),
        }),
        ...helper.getGenericClauses(totalCount, SHOW_SORT_MAP, [
            { date: "asc" },
            { id: "asc" },
        ]),
    });
    const availableShows = filteredShows.filter(
        (show) => !computeShowSoldOut(show.name, show.tickets),
    );

    return {
        zipCapTriggered: false,
        totalCount: Math.max(
            0,
            totalCount - (filteredShows.length - availableShows.length),
        ),
        shows: availableShows.map((show) => mapSearchShowToDTO(show, helper)),
    };
}

// Search DTO options: search fetches description + a profileId-keyed
// favoriteComedians block, emits description/popularityScore, uses the club
// image, and (unlike home) always computes distanceMiles — yielding null when no
// zip was searched, which cards use to hide the distance label.
function mapSearchShowToDTO(
    show: PublicShowRow,
    helper: QueryHelper,
    searchedZip?: string,
): ShowDTO {
    return mapShowRowToDTO(show, {
        userId: helper.getUserId(),
        zipCode: searchedZip,
        imageSource: "club",
        includeDescription: true,
        includePopularityScore: true,
        room: "raw",
        distanceWhenNoZip: "compute",
    });
}
