import { QueryProperty } from "../../enum/queryProperty";
import zipcodes from 'zipcodes';
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";
import { buildPaginationData } from "@/util/pagination";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    searchParams: URLSearchParams;
    slug?: string
    userId?: string;

    constructor(requestData: ParameterizedRequestData) {
        this.userId = requestData.userId
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
            NOT: {
                taggedComedians: {
                    some: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        };

        if (!filters) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedComedians: {
                        some: {
                            tag: {
                                value: {
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
            ...(this.userId
                ? {
                      favoriteComedians: {
                          where: {
                              user: {
                                  userId: this.userId,
                              },
                          },
                      },
                  }
                : {}),
        }
    }

    getFavoriteComedianClauseWithSelection() {
        return {
            ...(this.userId ? {
                favoriteComedians: {
                    where: {
                        user: {
                            id: this.userId
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

        const commonClause = {
            NOT: {
                taggedClubs: {
                    some: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        };

        if (!filters) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedClubs: {
                        some: {
                            tag: {
                                value: {
                                    in: filters.split(","),
                                    type: 'club'
                                },
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
    getShowFiltersClause() {
        const filters = this.searchParams.get(QueryProperty.Filters)
        const commonClause = {
            NOT: {
                taggedShows: {
                    some: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        };

        if (!filters) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedShows: {
                        some: {
                            tag: {
                                value: {
                                    in: filters.split(","),
                                    type: 'show'
                                },
                            },
                        },
                    },
                },
            ],
        };
    }


    getLineupItemClause() {
        const comedian = this.searchParams.get(QueryProperty.Comedian) as string;
        return {
            ...(comedian ? {
                // Lineup items represent shows where the comedian is on the lineup.
                // For every comedian query, we want to return to possibilities:
                lineupItems: {
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
                        },

                    },
                },
            } : {}),
        }
    }

    getZipCodeClause() {
        const providedZip = this.searchParams.get(QueryProperty.Zip) as string
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
        const fromDate = this.searchParams.get(QueryProperty.FromDate) as string
        const toDate = this.searchParams.get(QueryProperty.ToDate) as string
        const currentDate = new Date();
        const fromDateObj = fromDate ? new Date(fromDate) : currentDate;
        const isToday = fromDateObj.toDateString() === currentDate.toDateString();

        return {
            date: {
            gte: isToday ? currentDate.toISOString() : new Date(fromDateObj.setHours(0, 0, 0, 0)).toISOString(),
            ...(toDate ? { lte: new Date(toDate).toISOString() } : {})
            }
        }
    }

    getGenericClauses(total: number) {
        const sortBy = this.searchParams.get(QueryProperty.Sort) as string
        const direction = this.searchParams.get(QueryProperty.Direction) as string

        // Take the minimum number between the 'size=' param and the total results, which we got from a previous query. This is
        // basically our LIMIT value if this were SQL.
        const size = Number(this.searchParams.get(QueryProperty.Size) as string) ?? 10
        const take = Math.min(size, total)

        // Get the max number of pages, which we'll need to calculate our 'skip' value, which is essentially our starting index
        // The page itself will always be whatever is smaller: the page value provided or the max possible page. This is basically
        // our OFFSET value if this were SQL.
        const totalPages = Math.ceil(total / size);
        const page = Math.min(Number(this.searchParams.get(QueryProperty.Page)), totalPages) - 1

        // Our starting index is always our LIMIT size multiplied by our OFFSET
        const skip = take * page

        return {
            orderBy: {
                [sortBy]: direction,
            },
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

    getFilters() {
        return {
            filtersEmpty: this.searchParams.get(QueryProperty.Filters) == undefined,
            filters: this.searchParams.get(QueryProperty.Filters) ? (this.searchParams.get(QueryProperty.Filters) as string).split(",") : ['']
        }
    }

}
