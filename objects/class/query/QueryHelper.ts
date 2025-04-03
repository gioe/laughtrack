import { QueryProperty } from "../../enum/queryProperty";
import zipcodes from 'zipcodes';
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";
import { toZonedTime, format } from 'date-fns-tz';

// This class is meant to capture all of the page parameters that our Page URL contains and converts them into query parameters.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    searchParams: URLSearchParams;
    slug?: string
    profileId?: string;
    userId?: string;
    timezone: string

    constructor(requestData: ParameterizedRequestData) {
        this.timezone = requestData.timezone
        this.userId = requestData.userId
        this.profileId = requestData.profileId
        this.slug = requestData.slug ? decodeURI(requestData.slug) : undefined
        this.searchParams = new URLSearchParams(requestData.params)
    }

    // Comedians
    getComedianNameClause() {
        const comedian = this.searchParams.get(QueryProperty.Comedian) as string;

        if (!comedian) {
            return {}
        }

        return {
            name: {
                contains: comedian,
                mode: Prisma.QueryMode.insensitive,
            }
        }
    }

    getComedianFiltersClause() {
        const filters = this.searchParams.get(QueryProperty.Filters)
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
                                type: 'comedian'
                            },
                        },
                    },
                },
            ],
        };
    }

    getFavoriteComedianClause() {
        return {
            ...(this.getProfileId() ? {
                favoriteComedians: {
                    where: {
                        user: {
                            id: this.getProfileId()
                        }
                    },
                    select: {
                        id: true
                    }
                }
            } : {})
        }
    }

    setComedianName() {
        this.searchParams.set(QueryProperty.Comedian, this.slug ?? "")
    }

    // Clubs
    getClubNameClause() {
        const club = this.searchParams.get(QueryProperty.Club) as string
        if (!club) {
            return {}
        }

        return {
            name: {
                contains: club,
                mode: Prisma.QueryMode.insensitive,
            }
        }
    }

    getClubFiltersClause() {
        const filters = this.searchParams.get(QueryProperty.Filters)

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
                                type: 'club'
                            },
                        },
                    },
                },
            ],
        };
    }

    setClubName() {
        this.searchParams.set(QueryProperty.Club, this.slug ?? "")
    }

    // Shows
    getShowTagsClause() {
        const tags = this.searchParams.get(QueryProperty.Filters)

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
                                type: 'show'
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
        const comedian = this.searchParams.get(QueryProperty.Comedian) as string;
        return {
            lineupItems: {
                ...(comedian ? {
                    // Lineup items represent shows where the comedian is on the lineup.
                    // For every comedian query, we want to return to possibilities:
                    some: {
                        comedian: {
                            OR: [
                                // The comedian in the lineup item matches the supplieed query param and has no parent (meaning it is the parent)
                                {
                                    name: {
                                        contains: comedian,
                                        mode: Prisma.QueryMode.insensitive,
                                    },
                                    parentComedianId: null
                                },
                                // OR the comedian in the lineup's parent matches the query param.
                                {
                                    parentComedian: {
                                        name: {
                                            contains: comedian,
                                            mode: Prisma.QueryMode.insensitive,
                                        }
                                    }
                                }
                            ]
                        }
                    }
                } : {})
            }
        }
    }

    getZipCodeClause() {
        const providedZip = this.searchParams.get(QueryProperty.Zip) as string

        if (providedZip == "") return {}
        const radius = this.searchParams.get(QueryProperty.Distance) as string
        const zipResults = zipcodes.radius(providedZip, Number(radius));
        const nearbyZips = zipResults.map((zip: string | zipcodes.ZipCode) => typeof zip === 'string' ? zip : zip.zip);
        return {
            zipCode: {
                in: nearbyZips
            }
        }
    }

    getDateClause() {
        const fromDate = this.searchParams.get(QueryProperty.FromDate)
        const toDate = this.searchParams.get(QueryProperty.ToDate)
        if (!fromDate) {
            return {};
        }

        // Current time in UTC
        const currentDateUTC = new Date();

        // Convert fromDate midnight in timezone to UTC
        const fromDateMidnight = toZonedTime(`${fromDate}T00:00:00`, this.timezone);

        // Check if fromDate is today in the specified timezone
        const todayInTimezone = toZonedTime(format(new Date(), 'yyyy-MM-dd'), this.timezone);
        const isToday = fromDate === format(todayInTimezone, 'yyyy-MM-dd');

        let fromDateFilter = isToday ? currentDateUTC.toISOString() :  fromDateMidnight.toISOString()

          // Handle toDate if provided
        let toDateFilter: string | undefined = undefined;
        if (toDate) {
            // Convert end of day in specified timezone to UTC
            const toDateEndOfDay = toZonedTime(`${toDate}T23:59:59.999`, this.timezone);
            const oneDayInMs = 24 * 60 * 60 * 1000;
            toDateEndOfDay.setTime(toDateEndOfDay.getTime() - oneDayInMs);
            toDateFilter = toDateEndOfDay.toISOString();
        }

        return {
            date: {
              gte: fromDateFilter,
              ...(toDateFilter ? { lte: toDateFilter } : {})
            }
          };
        };

    getGenericClauses(total: number) {
        // Default values for pagination
        const defaultSize = 10;
        const defaultPage = 1;
        const defaultSortField = 'name';
        const defaultSortDirection = 'asc';

        // Get sort parameters with fallbacks
        const sortBy = this.searchParams.get(QueryProperty.Sort) || defaultSortField;
        const direction = this.searchParams.get(QueryProperty.Direction) || defaultSortDirection;

        // Handle pagination with proper null checks and defaults
        const size = Math.max(1, Number(this.searchParams.get(QueryProperty.Size)) || defaultSize);
        const take = Math.min(size, total);

        // Calculate pagination with safeguards
        const totalPages = Math.max(1, Math.ceil(total / size));
        const page = Math.max(1, Math.min(
            Number(this.searchParams.get(QueryProperty.Page)) || defaultPage,
            totalPages
        )) - 1;

        const skip = Math.max(0, take * page);

        // Ensure we always have valid sort parameters
        const sortParams = [
            { field: sortBy, direction: direction },
            { field: defaultSortField, direction: defaultSortDirection }
        ].filter(param => param.field && param.direction);

        return {
            orderBy: sortParams.map(param => ({
                [param.field]: param.direction
            })),
            take,
            skip,
        }
    }

    getZipCodes() {
        const providedZip = this.searchParams.get(QueryProperty.Zip) as string
        const radius = this.searchParams.get(QueryProperty.Distance) as string
        const nearbyZips = zipcodes.radius(providedZip, Number(radius))
        return {
            ...(nearbyZips ? {
                zipCode: {
                    in: nearbyZips
                }
            } : {})
        }
    }

    getSlug() {
        return this.slug
    }

    getUserId() {
        return this.userId
    }

    getProfileId() {
        return this.profileId
    }

    getFilters() {
        return {
            filtersEmpty: this.searchParams.get(QueryProperty.Filters) == undefined,
            filters: this.searchParams.get(QueryProperty.Filters) ? (this.searchParams.get(QueryProperty.Filters) as string).split(",") : ['']
        }
    }

}
