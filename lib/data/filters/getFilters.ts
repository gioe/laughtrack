import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface/filter.interface";
import { Filter } from "@/objects/class/filter/Filter";

export async function getFilters(type?: string, providedFilters?: string): Promise<Filter[]> {
    try {
        const filters = await db.tag.findMany({
            where: type ? {
                type: type
            } : undefined,
            select: {
                id: true,
                display: true,
                value: true,
                type: true,
                userFacing: true
            }
        });

        return filters.map(filter => ({
            id: filter.id,
            display: filter.display || '',
            value: filter.value || '',
            type: filter.type ? EntityType[filter.type] : EntityType.Show,
            userFacing: filter.userFacing
        })).filter((option) => option.userFacing).map((dto) => {
            return new Filter(dto, providedFilters ?? "")
        })
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
