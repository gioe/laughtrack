import { db } from "@/lib/db";

const EXCLUSIVITY_TAGS = ["Not A Real Comic"];

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
            NOT: {
                taggedComedians: {
                    some: {
                        tag: {
                            display: {
                                in: EXCLUSIVITY_TAGS,
                            },
                        },
                    },
                },
            },
        },
    });
}
