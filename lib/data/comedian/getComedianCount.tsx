import { db } from "@/lib/db";

export async function getComedianCount(params: any) {
    const { query, tagsEmpty, tags } = params;

    return db.comedian.count({
        where: {
            name: {
                contains: query,
                mode: "insensitive",
            },
            ...(!tagsEmpty
                ? {
                      taggedComedians: {
                          some: {
                              tag: {
                                  value: {
                                      in: tags,
                                  },
                              },
                          },
                      },
                  }
                : {}),
        },
    });
}
