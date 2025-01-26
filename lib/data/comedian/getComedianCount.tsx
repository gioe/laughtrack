import { db } from "@/lib/db";

export async function getComedianCount(params: any) {
    const { query, filtersEmpty, filters } = params;

    return db.comedian.count({
        where: {
            name: {
                contains: query,
                mode: "insensitive",
            },
            ...(!filtersEmpty
                ? {
                      taggedComedians: {
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
