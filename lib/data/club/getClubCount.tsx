import { db } from "@/lib/db";

export async function getClubCount(params: any) {
    const { query, tagsEmpty, tags } = params;

    return db.club.count({
        where: {
            name: {
                contains: query,
                mode: "insensitive",
            },
            ...(!tagsEmpty
                ? {
                      taggedClubs: {
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
