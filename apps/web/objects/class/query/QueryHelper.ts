import zipcodes from "zipcodes";
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";
import { SearchParams } from "@/objects/interface/showSearch.interface";
import { toZonedTime, format } from "date-fns-tz";
import { SortParamValue } from "@/objects/enum/sortParamValue";

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
        const providedZip = this.params.zip;
        const radius = this.params.distance;

        // Return empty object if no zip code or invalid zip code
        if (!providedZip || !/^\d{5}$/.test(providedZip)) {
            return {};
        }

        // If no valid radius, fall back to exact zip match so zip always scopes results
        const radiusNum = Number(radius);
        if (!radius || isNaN(radiusNum) || radiusNum < 1 || radiusNum > 500) {
            return { zipCode: { equals: providedZip } };
        }

        try {
            const zipResults = zipcodes.radius(providedZip, Number(radius));
            if (!zipResults || zipResults.length === 0) {
                return { zipCode: { equals: providedZip } };
            }

            const nearbyZips = zipResults.map(
                (zip: string | zipcodes.ZipCode) =>
                    typeof zip === "string" ? zip : zip.zip,
            );

            return {
                zipCode: {
                    in: nearbyZips,
                },
            };
        } catch (error) {
            console.error("Error in zip code radius calculation:", error);
            return { zipCode: { equals: providedZip } };
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
            return {};
        }
        if (
            toDate &&
            (!ISO_DATE_RE.test(toDate) || isNaN(new Date(toDate).getTime()))
        ) {
            return {};
        }

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

        // Handle toDate if provided
        let toDateFilter: string | undefined = undefined;
        if (toDate) {
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

    getGenericClauses(total: number) {
        // Default values for pagination
        const defaultSize = 10;
        const defaultPage = 1;
        const defaultSortField = SortParamValue.PopularityDesc;

        // Map full sort param values to database fields and directions
        const sortMap: Record<
            string,
            { field: string; direction: "asc" | "desc" }
        > = {
            [SortParamValue.NameAsc]: { field: "name", direction: "asc" },
            [SortParamValue.NameDesc]: { field: "name", direction: "desc" },
            [SortParamValue.ActivityAsc]: {
                field: "totalShows",
                direction: "asc",
            },
            [SortParamValue.ActivityDesc]: {
                field: "totalShows",
                direction: "desc",
            },
            [SortParamValue.DateAsc]: { field: "date", direction: "asc" },
            [SortParamValue.DateDesc]: { field: "date", direction: "desc" },
            [SortParamValue.PriceAsc]: { field: "price", direction: "asc" },
            [SortParamValue.PriceDesc]: { field: "price", direction: "desc" },
            [SortParamValue.PopularityAsc]: {
                field: "popularity",
                direction: "asc",
            },
            [SortParamValue.PopularityDesc]: {
                field: "popularity",
                direction: "desc",
            },
            [SortParamValue.TotalShowsAsc]: {
                field: "totalShows",
                direction: "asc",
            },
            [SortParamValue.TotalShowsDesc]: {
                field: "totalShows",
                direction: "desc",
            },
            [SortParamValue.ShowCountAsc]: {
                field: "totalShows",
                direction: "asc",
            },
            [SortParamValue.ShowCountDesc]: {
                field: "totalShows",
                direction: "desc",
            },
        };

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
        const sortEntry = sortMap[sortParam] ?? sortMap[defaultSortField];
        const { field: mappedField, direction: validDirection } = sortEntry;

        return {
            orderBy: [
                { [mappedField]: validDirection },
                ...(mappedField !== "name"
                    ? [
                          { totalShows: "desc" as const },
                          { name: "asc" as const },
                      ]
                    : []),
            ],
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
