import { db } from "@/lib/db";

const buildClubImageUrl = (clubName: string) => {
    return (
        new URL(
            `/clubs/${clubName}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    );
};

const buildComedianImageUrl = (name: string) => {
    return (
        new URL(
            `/comedians/${name}.png`,
            `https://${process.env.BUNNYCDN_CDN_HOST}/`,
        ) ?? new URL(`logo.png`, `https://${process.env.BUNNYCDN_CDN_HOST}/`)
    );
};

export async function getClubDetailPageData(params: any) {
    // Get filtered shows with basic info
    const filteredShows = await db.show.findMany({
        where: {
            club: {
                name: params.name,
            },
            date: {
                gt: new Date(),
            },
            ...(!params.tagsEmpty
                ? {
                      taggedShows: {
                          some: {
                              tag: {
                                  value: {
                                      in: params.tags,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
        select: {
            id: true,
            name: true,
            lastScrapedDate: true,
            date: true,
            popularity: true,
            ticketPrice: true,
            ticketPurchaseUrl: true,
            club: {
                select: {
                    id: true,
                    name: true,
                    website: true,
                    city: true,
                    address: true,
                    zipCode: true,
                },
            },
            lineupItems: {
                select: {
                    comedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            taggedComedians: {
                                where: {
                                    tag: {
                                        value: "alias",
                                    },
                                },
                                take: 1,
                            },
                            ...(params.userId && {
                                favoriteComedians: {
                                    where: {
                                        userId: Number(params.userId),
                                    },
                                    take: 1,
                                },
                            }),
                        },
                    },
                },
            },
        },
        orderBy: {
            [params.sortBy]: params.direction.toLowerCase(),
        },
        take: Number(params.size),
        skip: params.offset,
    });

    // Get total count
    const totalCount = await db.show.count({
        where: {
            club: {
                name: params.name,
            },
            date: {
                gt: new Date(),
            },
            ...(!params.tagsEmpty
                ? {
                      taggedShows: {
                          some: {
                              tag: {
                                  value: {
                                      in: params.tags,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
    });

    // Get club data
    const clubData = await db.club.findFirst({
        where: {
            name: params.name,
        },
        select: {
            id: true,
            name: true,
            website: true,
            city: true,
            address: true,
            zipCode: true,
        },
    });

    if (!clubData) {
        throw new Error(`Club with name ${params.clubName} not found`);
    }
    // Format the shows data
    const formattedShows = filteredShows.map((show) => {
        console.log(show);
        return {
            id: show.id,
            date: show.date,
            name: show.name,
            ticket: {
                price: show.ticketPrice,
                link: show.ticketPurchaseUrl,
            },
            club_name: show.club.name,
            address: show.club.address,
            lineup: show.lineupItems.map((item) => {
                return {
                    id: item.comedian.id,
                    name: item.comedian.name,
                    imageUr: buildComedianImageUrl(""),
                };
            }),
        };
    });

    return {
        response: {
            data: {
                name: clubData.name,
                id: clubData.id,
                imageUrl: buildClubImageUrl(clubData.name),
                website: clubData.website,
                city: clubData.city.name,
                address: clubData.address,
                zipCode: clubData.zipCode,
                dates: formattedShows,
            },
            total: totalCount,
        },
    };
}
