import { db } from "@/lib/db";

export interface ChainFilterDTO {
    id: number;
    name: string;
    slug: string;
    clubCount: number;
}

export async function getChainFilters(): Promise<ChainFilterDTO[]> {
    const chains = await db.chain.findMany({
        select: {
            id: true,
            name: true,
            slug: true,
            _count: {
                select: {
                    clubs: {
                        where: { visible: true, status: "active" },
                    },
                },
            },
        },
        orderBy: {
            clubs: { _count: "desc" },
        },
    });

    return chains
        .filter((c) => c._count.clubs > 0)
        .map((c) => ({
            id: c.id,
            name: c.name,
            slug: c.slug,
            clubCount: c._count.clubs,
        }));
}
