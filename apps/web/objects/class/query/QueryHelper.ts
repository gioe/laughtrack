import zipcodes from "zipcodes";
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";
import { SearchParams } from "@/objects/interface/showSearch.interface";
import { toZonedTime, format } from "date-fns-tz";
import { resolveLocationInput } from "@/util/location/resolveLocation";
import { SortParamValue } from "@/objects/enum/sortParamValue";

type SortEntry = { field: string; direction: "asc" | "desc" };
type SortMap = Record<string, SortEntry>;

/** Sort fields valid for the Show model (has: name, date, popularity). */
export const SHOW_SORT_MAP: SortMap = {
    [SortParamValue.NameAsc]: { field: "name", direction: "asc" },
    [SortParamValue.NameDesc]: { field: "name", direction: "desc" },
    [SortParamValue.DateAsc]: { field: "date", direction: "asc" },
    [SortParamValue.DateDesc]: { field: "date", direction: "desc" },
    [SortParamValue.PopularityAsc]: { field: "popularity", direction: "asc" },
    [SortParamValue.PopularityDesc]: {
        field: "popularity",
        direction: "desc",
    },
};

/**
 * Sort fields valid for the Comedian model (has: name, popularity, totalShows).
 * ShowCount sorts are handled via raw SQL in findComediansWithCount.
 */
export const COMEDIAN_SORT_MAP: SortMap = {
    [SortParamValue.NameAsc]: { field: "name", direction: "asc" },
    [SortParamValue.NameDesc]: { field: "name", direction: "desc" },
    [SortParamValue.ActivityAsc]: { field: "totalShows", direction: "asc" },
    [SortParamValue.ActivityDesc]: { field: "totalShows", direction: "desc" },
    [SortParamValue.PopularityAsc]: { field: "popularity", direction: "asc" },
    [SortParamValue.PopularityDesc]: {
        field: "popularity",
        direction: "desc",
    },
    [SortParamValue.TotalShowsAsc]: { field: "totalShows", direction: "asc" },
    [SortParamValue.TotalShowsDesc]: {
        field: "totalShows",
        direction: "desc",
    },
};

/** Sort fields valid for the Club model (has: name, popularity, totalShows). */
export const CLUB_SORT_MAP: SortMap = {
    [SortParamValue.NameAsc]: { field: "name", direction: "asc" },
    [SortParamValue.NameDesc]: { field: "name", direction: "desc" },
    [SortParamValue.ActivityAsc]: { field: "totalShows", direction: "asc" },
    [SortParamValue.ActivityDesc]: { field: "totalShows", direction: "desc" },
    [SortParamValue.PopularityAsc]: { field: "popularity", direction: "asc" },
    [SortParamValue.PopularityDesc]: {
        field: "popularity",
        direction: "desc",
    },
    [SortParamValue.TotalShowsAsc]: { field: "totalShows", direction: "asc" },
    [SortParamValue.TotalShowsDesc]: {
        field: "totalShows",
        direction: "desc",
    },
    [SortParamValue.ShowCountAsc]: { field: "totalShows", direction: "asc" },
    [SortParamValue.ShowCountDesc]: {
        field: "totalShows",
        direction: "desc",
    },
};

// This class is meant to capture all of the page parameters that our Page URL contains and converts them into query parameters.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {
    params: SearchParams;
    slug?: string;
    profileId?: string;
    userId?: string;
    timezone: string;

    constructor(requestData: ParameterizedRequestData) {
        this.timezone = requestData.timezone;
        this.userId = requestData.userId;
        this.profileId = requestData.profileId;
        this.slug = requestData.slug ? decodeURI(requestData.slug) : undefined;
        this.params = requestData.params;
    }

    // Comedians
    getComedianNameClause() {
        const comedian = this.params.comedian;

        if (!comedian) {
            return {};
        }

        return {
            name: {
                contains: comedian,
                mode: Prisma.QueryMode.insensitive,
            },
        };
    }

    getComedianFiltersClause() {
        const filters = this.params.filters;
        const commonClause = {
            taggedComedians: {
                none: {
                    tag: {
                        restrictContent: true,
                    },
                },
            },
        };

        if (!filters) {
            return commonClause;
        }

        return {
            ...commonClause,
            AND: [
                {
                    taggedComedians: {
                        some: {
                            tag: {
                                slug: {
                                    in: filters.split(","),
                                },
                                type: "comedian",
                            },
                        },
                    },
                },
            ],
        };
    }

    setComedianName() {
        this.params = { ...this.params, comedian: this.slug ?? "" };
    }

    // Clubs
    getClubNameClause() {
        const club = this.params.club;
        if (!club) {
            return {};
        }

        return {
            name: {
                contains: club,
                mode: Prisma.QueryMode.insensitive,
            },
        };
    }

    getClubFiltersClause() {
        const filters = this.params.filters;

        if (!filters) {
            return {};
        }

        return {
            AND: [
                {
                    taggedClubs: {
                        some: {
                            tag: {
                                slug: {
                                    in: filters.split(","),
                                },
                                type: "club",
                            },
                        },
                    },
                },
            ],
        };
    }

    setClubName() {
        this.params = { ...this.params, club: this.slug ?? "" };
    }

    // Shows
    getShowTagsClause() {
        const tags = this.params.filters;

        if (!tags) {
            return {};
        }

        return {
            AND: [
                {
                    taggedShows: {
                        some: {
                            tag: {
                                slug: {
                                    in: tags.split(","),
                                },
                                type: "show",
                            },
                        },
                    },
                },
            ],
        };
    }

    /**
     * Generates a Prisma query clause for filtering shows based on comedian lineup items.
     * This method constructs a query that matches shows where either:
     * 1. The comedian's name matches the search parameter directly (for parent comedians)
     * 2. The comedian's parent name matches the search parameter (for child comedians)
     *
     * @returns An object containing the lineup items clause if a comedian search parameter exists,
     * or an empty object if no comedian parameter is provided.
     *
     * @example
     * // With comedian search parameter "John"
     * // Returns shows where John is either directly in the lineup
     * // or where a comedian with John as their parent is in the lineup
     */
    getLineupItemClause() {
        const comedian = this.params.comedian;
        return {
            lineupItems: {
                ...(comedian
                    ? {
                          // Lineup items represent shows where the comedian is on the lineup.
                          // For every comedian query, we want to return to possibilities:
                          some: {
                              comedian: {
                                  OR: [
                                      // The comedian in the lineup item matches the supplieed query param and has no parent (meaning it is the parent)
                                      {
                                          name: {
                                              contains: comedian,
                                              mode: Prisma.QueryMode
                                                  .insensitive,
                                          },
                                          parentComedianId: null,
                                      },
                                      // OR the comedian in the lineup's parent matches the query param.
                                      {
                                          parentComedian: {
                                              name: {
                                                  contains: comedian,
                                                  mode: Prisma.QueryMode
                                                      .insensitive,
                                              },
                                          },
                                      },
                                  ],
                              },
                          },
                      }
                    : {}),
            },
        };
    }

    getZipCodeClause() {
        const input = this.params.zip;
        const radius = this.params.distance;

        if (!input) return {};

        const resolution = resolveLocationInput(input);

        // City name not found — return a clause that matches nothing
        if (!resolution.found) {
            return { zipCode: { equals: "" } };
        }

        const { startingZips } = resolution;
        const radiusNum = Number(radius);

        // No valid radius — exact match on the starting zip(s)
        if (!radius || isNaN(radiusNum) || radiusNum < 1 || radiusNum > 500) {
            return startingZips.length === 1
                ? { zipCode: { equals: startingZips[0] } }
                : { zipCode: { in: startingZips } };
        }

        // Expand each starting zip by the radius and combine results.
        // For ambiguous city names (e.g. "Portland" → OR, ME, TN …) this
        // returns zips from every matching metro area.
        try {
            const allNearbyZips = new Set<string>();
            for (const startZip of startingZips) {
                const zipResults = zipcodes.radius(startZip, radiusNum);
                if (zipResults) {
                    zipResults.forEach((zip: string | zipcodes.ZipCode) => {
                        allNearbyZips.add(
                            typeof zip === "string" ? zip : zip.zip,
                        );
                    });
                }
            }

            if (allNearbyZips.size === 0) {
                return { zipCode: { in: startingZips } };
            }

            return { zipCode: { in: Array.from(allNearbyZips) } };
        } catch (error) {
            console.error("Error in zip code radius calculation:", error);
            return { zipCode: { in: startingZips } };
        }
    }

    getDateClause() {
        const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
        const fromDate = this.params.fromDate;
        const toDate = this.params.toDate;
        if (
            !fromDate ||
            !ISO_DATE_RE.test(fromDate) ||
            isNaN(new Date(fromDate).getTime())
        ) {
            // No valid fromDate provided — default to upcoming shows only
            return { date: { gte: new Date().toISOString() } };
        }
        const toDateValid =
            !toDate ||
            (ISO_DATE_RE.test(toDate) && !isNaN(new Date(toDate).getTime()));

        // Current time in UTC
        const currentDateUTC = new Date();

        // Convert fromDate midnight in timezone to UTC
        const fromDateMidnight = toZonedTime(
            `${fromDate}T00:00:00`,
            this.timezone,
        );

        // Check if fromDate is today in the specified timezone
        const todayInTimezone = toZonedTime(
            format(new Date(), "yyyy-MM-dd"),
            this.timezone,
        );
        const isToday = fromDate === format(todayInTimezone, "yyyy-MM-dd");

        const fromDateFilter = isToday
            ? currentDateUTC.toISOString()
            : fromDateMidnight.toISOString();

        // Handle toDate if provided and valid
        let toDateFilter: string | undefined = undefined;
        if (toDate && toDateValid) {
            // Convert end of day in specified timezone to UTC
            const toDateEndOfDay = toZonedTime(
                `${toDate}T23:59:59.999`,
                this.timezone,
            );
            const oneDayInMs = 24 * 60 * 60 * 1000;
            toDateEndOfDay.setTime(toDateEndOfDay.getTime() - oneDayInMs);
            toDateFilter = toDateEndOfDay.toISOString();
        }

        return {
            date: {
                gte: fromDateFilter,
                ...(toDateFilter ? { lte: toDateFilter } : {}),
            },
        };
    }

    getGenericClauses(
        total: number,
        sortMap: SortMap,
        tiebreakers?: Record<string, "asc" | "desc">[],
    ) {
        // Default values for pagination
        const defaultSize = 10;
        const defaultPage = 1;
        const defaultSortField = SortParamValue.PopularityDesc;

        const effectiveSortMap = sortMap;

        // Handle pagination with proper null checks and defaults
        const size = Math.max(1, Number(this.params.size) || defaultSize);
        const take = Math.min(size, total);

        // Calculate pagination with safeguards
        const totalPages = Math.max(1, Math.ceil(total / size));
        const page =
            Math.max(
                1,
                Math.min(Number(this.params.page) || defaultPage, totalPages),
            ) - 1;

        const skip = Math.max(0, take * page);

        // Look up full sort param; invalid values fall back to popularity_desc
        const sortParam = this.params.sort || defaultSortField;
        const sortEntry =
            effectiveSortMap[sortParam] ?? effectiveSortMap[defaultSortField];
        const { field: mappedField, direction: validDirection } = sortEntry;

        // When tiebreakers are provided explicitly (e.g. shows use date+id to
        // avoid nullable name), use them unconditionally. Otherwise fall back to
        // the default name-asc tiebreaker, skipping it when name is already the
        // primary sort field.
        const tiebreakerEntries: Record<string, "asc" | "desc">[] =
            tiebreakers ??
            (mappedField !== "name" ? [{ name: "asc" as const }] : []);

        return {
            orderBy: [{ [mappedField]: validDirection }, ...tiebreakerEntries],
            take,
            skip,
        };
    }

    getSlug() {
        return this.slug;
    }

    getUserId() {
        return this.userId;
    }

    getProfileId() {
        return this.profileId;
    }

    getFilters() {
        return {
            filtersEmpty: this.params.filters == undefined,
            filters: this.params.filters
                ? this.params.filters.split(",")
                : [""],
        };
    }
}
