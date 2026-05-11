import { db } from "@/lib/db";
import { filterAndMapLineupItems } from "@/util/comedian/comedianUtil";
import { buildClubImageUrl } from "@/util/imageUtil";
import { mapTickets } from "@/util/ticket/ticketUtil";
import { Prisma } from "@prisma/client";
import { fromZonedTime } from "date-fns-tz";

const ISO_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

const UPCOMING_RUN_SHOW_SELECT = {
    id: true,
    name: true,
    date: true,
    description: true,
    room: true,
    tickets: {
        select: {
            price: true,
            soldOut: true,
            purchaseUrl: true,
            type: true,
        },
    },
    club: {
        select: {
            id: true,
            name: true,
            address: true,
            city: true,
            state: true,
            country: true,
            zipCode: true,
            hasImage: true,
            timezone: true,
        },
    },
    lineupItems: {
        where: {
            comedian: {
                taggedComedians: {
                    none: {
                        tag: {
                            userFacing: false,
                        },
                    },
                },
            },
        },
        select: {
            comedian: {
                select: {
                    id: true,
                    uuid: true,
                    name: true,
                    hasImage: true,
                    _count: {
                        select: {
                            lineupItems: true,
                        },
                    },
                    parentComedian: {
                        select: {
                            id: true,
                            uuid: true,
                            name: true,
                            hasImage: true,
                            _count: {
                                select: {
                                    lineupItems: true,
                                },
                            },
                            taggedComedians: {
                                select: {
                                    tag: true,
                                },
                            },
                        },
                    },
                    taggedComedians: {
                        select: {
                            tag: true,
                        },
                    },
                },
            },
        },
    },
} as const;

export interface UpcomingRunsFilters {
    club?: string;
    location?: string;
    date?: string;
    timezone: string;
    profileId?: string;
    userId?: string;
}

export interface UpcomingComedianRun {
    clubID: number;
    clubName: string;
    clubImageUrl: string;
    shows: ReturnType<typeof mapUpcomingRunShow>[];
}

export async function findUpcomingRunsForComedian(
    comedianId: number,
    filters: UpcomingRunsFilters,
): Promise<UpcomingComedianRun[]> {
    const comedian = await db.comedian.findUnique({
        where: { id: comedianId },
        select: { id: true, uuid: true },
    });

    if (!comedian) return [];

    const where: Prisma.ShowWhereInput = {
        date: buildDateClause(filters),
        club: {
            visible: true,
            ...(filters.club
                ? {
                      name: {
                          contains: filters.club,
                          mode: Prisma.QueryMode.insensitive,
                      },
                  }
                : {}),
            ...(filters.location
                ? {
                      OR: [
                          { address: locationContains(filters.location) },
                          { city: locationContains(filters.location) },
                          { state: locationContains(filters.location) },
                          { country: locationContains(filters.location) },
                          { zipCode: locationContains(filters.location) },
                      ],
                  }
                : {}),
        },
        lineupItems: {
            some: {
                comedian: {
                    OR: [
                        { id: comedian.id },
                        { uuid: comedian.uuid },
                        { parentComedianId: comedian.id },
                    ],
                },
            },
        },
    };

    const shows = await db.show.findMany({
        where,
        select: {
            ...UPCOMING_RUN_SHOW_SELECT,
            lineupItems: {
                ...UPCOMING_RUN_SHOW_SELECT.lineupItems,
                select: {
                    comedian: {
                        select: {
                            ...UPCOMING_RUN_SHOW_SELECT.lineupItems.select
                                .comedian.select,
                            ...(filters.profileId
                                ? {
                                      favoriteComedians: {
                                          where: {
                                              profileId: filters.profileId,
                                          },
                                          select: {
                                              id: true,
                                          },
                                      },
                                  }
                                : {}),
                        },
                    },
                },
            },
        },
        orderBy: [{ date: "asc" }, { id: "asc" }],
    });

    return groupConsecutiveRuns(
        shows.map((show) => mapUpcomingRunShow(show, filters.userId)),
    );
}

function buildDateClause(filters: UpcomingRunsFilters): Prisma.DateTimeFilter {
    if (filters.date && ISO_DATE_RE.test(filters.date)) {
        return {
            gte: fromZonedTime(`${filters.date}T00:00:00`, filters.timezone),
            lte: fromZonedTime(
                `${filters.date}T23:59:59.999`,
                filters.timezone,
            ),
        };
    }

    return { gte: new Date() };
}

function locationContains(value: string) {
    return {
        contains: value,
        mode: Prisma.QueryMode.insensitive,
    };
}

function mapUpcomingRunShow(
    show: Prisma.ShowGetPayload<{ select: typeof UPCOMING_RUN_SHOW_SELECT }>,
    userId?: string,
) {
    return {
        id: show.id,
        date: show.date,
        name: show.name,
        description: show.description ?? undefined,
        room: show.room,
        address: show.club.address,
        clubID: show.club.id,
        clubName: show.club.name,
        imageUrl: buildClubImageUrl(show.club.name, show.club.hasImage),
        soldOut:
            show.tickets.length > 0 &&
            show.tickets.every((ticket) => ticket.soldOut === true),
        lineup: filterAndMapLineupItems(show.lineupItems, userId),
        tickets: mapTickets(show.tickets),
        distanceMiles: null,
        timezone: show.club.timezone,
    };
}

function groupConsecutiveRuns(
    shows: ReturnType<typeof mapUpcomingRunShow>[],
): UpcomingComedianRun[] {
    return shows.reduce<UpcomingComedianRun[]>((runs, show) => {
        const last = runs[runs.length - 1];
        if (last && last.clubID === show.clubID) {
            last.shows.push(show);
            return runs;
        }

        runs.push({
            clubID: show.clubID,
            clubName: show.clubName ?? "Unknown club",
            clubImageUrl: show.imageUrl,
            shows: [show],
        });
        return runs;
    }, []);
}
