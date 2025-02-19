import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { QueryProperty } from "@/objects/enum";

export async function getFilters(type: string, queryParams: URLSearchParams): Promise<FilterDTO[]> {

    try {
        const queriedFilters = await db.tag.findMany({
            where: {
                type: type,
                userFacing: true
            },
            select: {
                id: true,
                display: true,
                value: true,
            }
        });

        return queriedFilters.map(queriedFilter => ({
            id: queriedFilter.id,
            display: queriedFilter.display || '',
            value: queriedFilter.value || '',
            selected: queryParams.get(QueryProperty.Filters)?.includes(queriedFilter.value) || false
        }))

    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
