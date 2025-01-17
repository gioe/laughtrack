import { db } from "@/lib/db";
import { buildClubImageUrl } from "@/util/imageUtil";

export async function findClubs(params: any) {
    const { query, tags, tagsEmpty, sortBy, direction, size, offset } = params;

    const filteredClubs = await db.club.findMany({
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
        select: {
            id: true,
            name: true,
            address: true,
            website: true,
            zipCode: true,
        },
        orderBy: {
            [sortBy]: direction,
        },
        take: Number(size),
        skip: offset,
    });

    return filteredClubs.map((club) => {
        return {
            id: club.id,
            name: club.name,
            address: club.address,
            zipCode: club.zipCode,
            imageUrl: buildClubImageUrl(club.name),
        };
    });
}
