import { db } from "@/lib/db"

export async function getShowCount(params: any): Promise<number> {
    const { clubName, city, comedianName, from_date, to_date, filtersEmpty, filters } = params

    return await db.show.count({
        where: {
            club: {
                ...(clubName ? {
                    name: clubName
                } : {}),
                city: {
                    name: city
                }
            },
            ...(comedianName ?
                {
                    lineupItems: {
                        some: {
                            comedian: {
                                name: comedianName,
                            },
                        },
                    },
                } : {}),
            date: {
                gte: from_date ? new Date(from_date).toISOString() : new Date().toISOString(),
                ...(to_date ? { lte: new Date(to_date).toISOString() } : {})
            },
            ...(!filtersEmpty ? {
                taggedShows: {
                    some: {
                        tag: {
                            display: {
                                in: filters
                            }
                        }
                    }
                }
            } : {})
        }
    })
}
