import { QueryProperty } from "../../enum/queryProperty";
import zipcodes from 'zipcodes';
import { Prisma } from "@prisma/client";
import { ParameterizedRequestData } from "@/objects/interface";

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
        this.slug = requestData.slug
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

        if (!this.searchParams.get(QueryProperty.Filters)) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedComedians: {
                        some: {
                            tag: {
                                display: {
                                    in: (this.searchParams.get(QueryProperty.Filters) as string).split(","),
                                },
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

        if (!this.searchParams.get(QueryProperty.Filters)) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedClubs: {
                        some: {
                            tag: {
                                display: {
                                    in: (this.searchParams.get(QueryProperty.Filters) as string).split(","),
                                },
                            },
                        },
                    },
                },
            ],
        };
    }

    // Shows
    getShowFiltersClause() {
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

        if (!this.searchParams.get(QueryProperty.Filters)) {
            return commonClause;
        }

        return {
            AND: [
                commonClause,
                {
                    taggedShows: {
                        some: {
                            tag: {
                                display: {
                                    in: (this.searchParams.get(QueryProperty.Filters) as string).split(","),
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
        return {
            date: {
                gte: fromDate ? new Date(fromDate).toISOString() : new Date().toISOString(),
                // If a Less Than (lte) paramater is provided, include that.
                ...(toDate ? { lte: new Date(toDate).toISOString() } : {})
            }
        }
    }

    getGenericClauses() {
        const sortBy = this.searchParams.get(QueryProperty.Sort) as string
        const direction = this.searchParams.get(QueryProperty.Direction) as string
        const size = Number(this.searchParams.get(QueryProperty.Size) as string) ?? 10
        const page = Number(this.searchParams.get(QueryProperty.Page)) - 1
        const offset = size * page
        return {
            orderBy: {
                [sortBy]: direction,
            },
            take: size,
            skip: offset,
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

    getUserId() {
        return this.userId
    }

    getNameSlug() {
        return this.slug
    }

    getIdSlug() {
        return this.slug
    }

    getFilters() {
        return {
            filtersEmpty: this.searchParams.get(QueryProperty.Filters) == undefined,
            filters: this.searchParams.get(QueryProperty.Filters) ? (this.searchParams.get(QueryProperty.Filters) as string).split(",") : ['']
        }
    }

}
