import { ParamsDictValue, SearchParamsHelper } from "../params/SearchParamsHelper";
import { allQueryProperties, DEFAULT_ERROR, QueryProperty } from "../../enum/queryProperty";
import { DynamicRoute } from "../../interface/identifable.interface";
import zipcodes from 'zipcodes';
import { Prisma } from "@prisma/client";

// This class is meant to capture all of the page parameters that Next provides us with.
// These are relevant for DB querying and their existence persists across all pages so we capture it
// as globally as possible, updating values according to page transitions.
// It is almost certainly too bloated.
export class QueryHelper {

    identifier?: DynamicRoute
    searchParamsHelper: SearchParamsHelper;
    filters?: string
    userId?: string;

    constructor(searchParamsHelper: SearchParamsHelper,
        filters?: string,
        identifier?: DynamicRoute,
        userId?: string) {
        this.userId = userId
        this.identifier = identifier
        this.filters = filters
        this.searchParamsHelper = searchParamsHelper
    }

    // Comedians
    getComedianNameClause() {
        return {
            name: {
                contains: this.searchParamsHelper.getParamValue(QueryProperty.Comedian) as string,
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

        if (!this.filters) {
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
                                    in: this.filters.split(","),
                                },
                            },
                        },
                    },
                },
            ],
        };
    }

    getFavoriteComedianClause() {
        const userId = this.userId;
        return {
            ...(userId
                ? {
                      favoriteComedians: {
                          where: {
                              user: {
                                  userId,
                              },
                          },
                      },
                  }
                : {}),
        }
    }

    getFavoriteComedianClauseWithSelection() {
        const userId = this.userId;
        return {
            ...(userId ? {
                favoriteComedians: {
                    where: {
                        user: {
                            id: userId
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
        return {
            name: {
                contains: this.searchParamsHelper.getParamValue(QueryProperty.Club) as string,
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

        if (!this.filters) {
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
                                    in: this.filters.split(","),
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

        if (!this.filters) {
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
                                    in: this.filters.split(","),
                                },
                            },
                        },
                    },
                },
            ],
        };
    }


    getLineupItemClause() {
        const comedian = this.searchParamsHelper.getParamValue(QueryProperty.Comedian) as string;
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
        const providedZip = this.searchParamsHelper.getParamValue(QueryProperty.Zip) as string
        const radius = this.searchParamsHelper.getParamValue(QueryProperty.Distance) as string
        const zipResults = zipcodes.radius(providedZip, Number(radius));
        const nearbyZips = zipResults.map(zip => typeof zip === 'string' ? zip : zip.zip);
        return {
            zipCode: {
                in: nearbyZips
            }
        }
    }

    getDateClause() {
        const fromDate = this.searchParamsHelper.getParamValue(QueryProperty.FromDate) as string
        const toDate = this.searchParamsHelper.getParamValue(QueryProperty.ToDate) as string
        return {
            date: {
                gte: fromDate ? new Date(fromDate).toISOString() : new Date().toISOString(),
                // If a Less Than (lte) paramater is provided, include that.
                ...(toDate ? { lte: new Date(toDate).toISOString() } : {})
            }
        }
    }

    getGenericClauses() {
        const sortBy = this.searchParamsHelper.getParamValue(QueryProperty.Sort) as string
        const direction = this.searchParamsHelper.getParamValue(QueryProperty.Direction) as string
        const size = Number(this.searchParamsHelper.getParamValue(QueryProperty.Size) as string) ?? 10
        const page = Number(this.searchParamsHelper.getParamValue(QueryProperty.Page)) - 1
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
        const providedZip = this.searchParamsHelper.getParamValue(QueryProperty.Zip) as string
        const radius = this.searchParamsHelper.getParamValue(QueryProperty.Distance) as string
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
        return this.identifier?.name
    }

    getIdSlug() {
        return this.identifier?.id
    }

    getFilters() {
        return {
            filtersEmpty: this.filters == undefined,
            filters: this.filters ? this.filters.split(",") : ['']
        }
    }

    getDomainParams() {
        const paramsMap = new Map<string, ParamsDictValue>()
        for (const [key, value] of this.searchParamsHelper.paramsDict.entries()) {
            if (!allQueryProperties.includes(key)) {
                paramsMap.set(key, value)
            }
        }
        return Object.fromEntries(paramsMap.entries())
    }


    static async storePageParams(searchParams: URLSearchParams, userId?: string,) {
        const searchParamsHelper = new SearchParamsHelper(searchParams)
        return new QueryHelper(searchParamsHelper, userId)
    }

}
