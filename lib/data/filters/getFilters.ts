import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
import { Filter } from "@/objects/class/filter/Filter";

export async function getFilters(type: string, params: any): Promise<Filter[]> {
    const { filters } = params

    try {
        const queriedFilters = await db.tag.findMany({
            where: {
                type: type
            },
            select: {
                id: true,
                display: true,
                value: true,
                type: true,
                userFacing: true
            }
        });

        return queriedFilters.map(queriedFilter => ({
            id: queriedFilter.id,
            display: queriedFilter.display || '',
            value: queriedFilter.value || '',
            type: queriedFilter.type ? EntityType[queriedFilter.type] : EntityType.Show,
            userFacing: queriedFilter.userFacing
        })).filter((option) => option.userFacing).map((dto) => new Filter(dto, filters ?? ""))

    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
