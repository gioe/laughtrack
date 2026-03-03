import { db } from "@/lib/db";
import { Prisma, TagVisibility } from "@prisma/client";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { QueryProperty } from "@/objects/enum";
import { paramsContainsFilter } from "@/util/filter/util";
import { EntityType } from "@/objects/enum";

const TAG_SELECT = {
    id: true,
    slug: true,
    name: true,
} as const;

export async function getFilters(
    type: EntityType,
    queryParams: URLSearchParams
): Promise<FilterDTO[]> {
    try {
        if (!Object.values(EntityType).includes(type)) {
            throw new Error(`Invalid entity type: ${type}`);
        }

        const queriedFilters = await db.tag.findMany({
            where: {
                type: type,
                visibility: TagVisibility.PUBLIC,
                AND: [
                    {
                        OR: [
                            { name: { not: null } },
                            { slug: { not: null } }
                        ]
                    }
                ]
            },
            select: TAG_SELECT,
            orderBy: {
                name: 'asc'
            }
        });

        const filters = queryParams.get(QueryProperty.Filters);

        return queriedFilters.map(filter => ({
            id: filter.id,
            name: filter.name ?? '',
            slug: filter.slug ?? '',
            selected: paramsContainsFilter(filters, filter.slug)
        }));
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error('Database error in getFilters:', error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error('Error in getFilters:', error);
            throw error;
        }
        throw new Error('An unknown error occurred while fetching filters');
    }
}
