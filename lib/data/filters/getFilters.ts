import { db } from "@/lib/db";
import { Prisma, TagVisibility } from "@prisma/client";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { QueryProperty } from "@/objects/enum";
import { paramsContainsFilter } from "@/util/filter/util";

export async function getFilters(type: string, queryParams: URLSearchParams): Promise<FilterDTO[]> {

    try {
        const queriedFilters = await db.tag.findMany({
            where: {
                type: type,
                visibility: TagVisibility.PUBLIC,
            },
            select: {
                id: true,
                slug: true,
                name: true,
            }
        });

        return queriedFilters.map(queriedFilter => ({
            id: queriedFilter.id,
            name: queriedFilter.name || '',
            slug: queriedFilter.slug || '',
            selected: paramsContainsFilter(queryParams.get(QueryProperty.Filters), queriedFilter.slug)
        }))

    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
