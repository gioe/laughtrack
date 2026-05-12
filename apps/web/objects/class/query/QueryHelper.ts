import zipcodes from "zipcodes";
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";
import { SearchParams } from "@/objects/interface/showSearch.interface";
import { toZonedTime, fromZonedTime, format } from "date-fns-tz";
import { resolveLocationInput } from "@/util/location/resolveLocation";
import { SortParamValue } from "@/objects/enum/sortParamValue";

/**
 * Synthetic slug reserved inside the `filters` URL CSV that flags the Free
 * filter on shows search. Lives in the existing `filters` param (e.g.
 * `?filters=open-mic,free`) rather than a dedicated `free=true` boolean so the
 * existing chip/modal UX renders it without per-filter wiring. No `Tag` row
 * uses this slug — `getFreeShowsClause` translates it to a ticket-price
 * predicate and `getShowTagsClause` strips it before querying tags.
 *
 * Qualification: a show matches when ANY of its tickets has price = 0 OR
 * price IS NULL. A mixed-price show (one paid + one free tier) still
 * qualifies, since the user wants to discover that a free option exists.
 */
export const FREE_FILTER_SLUG = "free";

/**
 * Exact-match check for FREE_FILTER_SLUG inside a `filters` CSV. Required
 * because the CSV is parsed at multiple sites (where-clause builders, UI
 * synthetic-FilterDTO injection) and a naive substring check would
 * false-positive against any tag slug containing "free" (e.g. "freestyle").
 */
export function isFreeFilterSelected(
    filters: string | null | undefined,
): boolean {
    if (!filters) return false;
    return filters.split(",").some((slug) => slug === FREE_FILTER_SLUG);
}

type SortEntry = {
    field: string;
    direction: "asc" | "desc";
    // When set, emits Prisma's verbose orderBy shape so NULL placement is
    // explicit. Required for nullable columns like Show.minPrice where the
    // Postgres defaults (ASC NULLS LAST, DESC NULLS FIRST) disagree with the
    // intended UX (NULLs always at the bottom regardless of direction).
    nulls?: "first" | "last";
};
type SortMap = Record<string, SortEntry>;

/**
 * Sort fields valid for the Show model.
 *
 * minPrice is the denormalized cheapest *paid* ticket on the show, maintained
 * by the tickets_trickle_show_min_price trigger. nulls:"last" both directions
 * keeps shows with no priced tickets (RSVP-only / not yet scraped) at the
 * bottom so the price sort never leads with a row that has no price to
 * compare. Free-show discoverability is handled by TASK-2141's Free filter.
 */
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
    [SortParamValue.PriceAsc]: {
        field: "minPrice",
        direction: "asc",
        nulls: "last",
    },
    [SortParamValue.PriceDesc]: {
        field: "minPrice",
        direction: "desc",
        nulls: "last",
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

/** Admin-only sort fields appended to COMEDIAN_SORT_MAP. */
export const COMEDIAN_SORT_MAP_ADMIN: SortMap = {
    ...COMEDIAN_SORT_MAP,
    [SortParamValue.InsertedAtDesc]: { field: "id", direction: "desc" },
    [SortParamValue.InsertedAtAsc]: { field: "id", direction: "asc" },
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
    private static readonly ZIP_CAP = 500;

    params: SearchParams;
    slug?: string;
    profileId?: string;
    userId?: string;
    timezone: string;
    isAdmin: boolean;
    private _zipCapTriggered = false;
    private _exactClubNameMatch = false;

    constructor(requestData: ParameterizedRequestData) {
        this.timezone = requestData.timezone;
        this.userId = requestData.userId;
        this.profileId = requestData.profileId;
        this.slug = requestData.slug ? decodeURI(requestData.slug) : undefined;
        this.params = requestData.params;
        this.isAdmin = requestData.isAdmin ?? false;
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

        // Detail-page context (setClubName) needs exact match so that clubs
        // whose names are substrings of each other (e.g. "The Stand" vs
        // "The Stand Up Comedy Club") don't bleed into each other's show lists.
        return {
            name: {
                ...(this._exactClubNameMatch
                    ? { equals: club }
                    : { contains: club }),
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

    getChainClause() {
        const chain = this.params.chain;
        if (!chain) {
            return {};
        }
        return {
            chain: { slug: chain },
        };
    }

    setClubName() {
        this.params = { ...this.params, club: this.slug ?? "" };
        this._exactClubNameMatch = true;
    }

    // Shows
    getShowTagsClause() {
        const tags = this.params.filters;

        if (!tags) {
            return {};
        }

        // FREE_FILTER_SLUG is not a real Tag — it's a synthetic flag handled
        // by getFreeShowsClause. Drop it before querying taggedShows so a CSV
        // of just "free" doesn't AND in an empty-result tag predicate.
        const tagSlugs = tags
            .split(",")
            .filter((slug) => slug && slug !== FREE_FILTER_SLUG);

        if (tagSlugs.length === 0) {
            return {};
        }

        return {
            AND: [
                {
                    taggedShows: {
                        some: {
                            tag: {
                                slug: {
                                    in: tagSlugs,
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
     * Prisma `Show.where` fragment for the Free filter. Returns `{}` when
     * FREE_FILTER_SLUG is absent from `params.filters`, otherwise narrows to
     * shows that have at least one ticket with price = 0 OR price IS NULL.
     */
    getFreeShowsClause() {
        if (!isFreeFilterSelected(this.params.filters)) {
            return {};
        }
        return {
            tickets: {
                some: {
                    OR: [{ price: 0 }, { price: null }],
                },
            },
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

            let zips = Array.from(allNearbyZips);
            if (zips.length > QueryHelper.ZIP_CAP) {
                console.warn(
                    `[QueryHelper] zip IN clause capped at ${QueryHelper.ZIP_CAP} (city="${input}", raw count=${zips.length}). ` +
                        `Try including a state abbreviation (e.g. "Portland, OR") for a more precise result.`,
                );
                zips = zips.slice(0, QueryHelper.ZIP_CAP);
                this._zipCapTriggered = true;
            }

            return { zipCode: { in: zips } };
        } catch (error) {
            console.error("Error in zip code radius calculation:", error);
            return { zipCode: { in: startingZips } };
        }
    }

    isZipCapTriggered(): boolean {
        return this._zipCapTriggered;
    }

    getDateClause() {
        const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
        const fromDate = this.params.fromDate;
        const toDate = this.params.toDate;
        const fromDateValid =
            !!fromDate &&
            ISO_DATE_RE.test(fromDate) &&
            !isNaN(new Date(fromDate).getTime());
        const toDatePresent =
            !!toDate &&
            ISO_DATE_RE.test(toDate) &&
            !isNaN(new Date(toDate).getTime());

        // No valid date params — return an empty clause. Callers add their own
        // upcoming-only constraint (date.gte = now) when they need one.
        if (!fromDateValid && !toDatePresent) {
            return {};
        }
        if (!fromDateValid) {
            // fromDate missing/invalid but toDate is present and valid — fall
            // back to upcoming-only (gte:now). Preserves the pre-refactor
            // behavior for this edge case so a stray toDate still bounds results.
            return { date: { gte: new Date().toISOString() } };
        }
        const toDateValid =
            !toDate ||
            (ISO_DATE_RE.test(toDate) && !isNaN(new Date(toDate).getTime()));

        // Current time in UTC
        const currentDateUTC = new Date();

        // Convert fromDate midnight in user's timezone to UTC
        const fromDateMidnight = fromZonedTime(
            `${fromDate}T00:00:00`,
            this.timezone,
        );

        // Check if fromDate is today in the specified timezone
        const nowInTimezone = toZonedTime(new Date(), this.timezone);
        const isToday = fromDate === format(nowInTimezone, "yyyy-MM-dd");

        const fromDateFilter = isToday
            ? currentDateUTC.toISOString()
            : fromDateMidnight.toISOString();

        // Handle toDate if provided and valid
        let toDateFilter: string | undefined = undefined;
        if (toDate && toDateValid) {
            // Convert end of day in user's timezone to UTC
            const toDateEndOfDay = fromZonedTime(
                `${toDate}T23:59:59.999`,
                this.timezone,
            );
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
        const {
            field: mappedField,
            direction: validDirection,
            nulls,
        } = sortEntry;

        // When tiebreakers are provided explicitly (e.g. shows use date+id to
        // avoid nullable name), use them unconditionally. Otherwise fall back to
        // the default name-asc tiebreaker, skipping it when name is already the
        // primary sort field.
        const tiebreakerEntries: Record<string, "asc" | "desc">[] =
            tiebreakers ??
            (mappedField !== "name" ? [{ name: "asc" as const }] : []);

        const primaryOrder = nulls
            ? { [mappedField]: { sort: validDirection, nulls } }
            : { [mappedField]: validDirection };

        return {
            orderBy: [primaryOrder, ...tiebreakerEntries],
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
