import { db } from "@/lib/db";

export async function getClubCount(params: any) {
    const { query, filtersEmpty, filters } = params;

    return db.club.count({
        where: {
            name: {
                contains: query,
                mode: "insensitive",
            },
            ...(!filtersEmpty
                ? {
                      taggedClubs: {
                          some: {
                              tag: {
                                  display: {
                                      in: filters,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
    });
}
