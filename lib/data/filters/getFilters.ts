import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
import { FilterDTO } from "@/objects/interface/filter.interface";

export async function getFilters(type?: string): Promise<FilterDTO[]> {
    try {
        const tags = await db.tag.findMany({
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

        return tags.map(tag => ({
            id: tag.id,
            display: tag.display || '',
            value: tag.value || '',
            type: tag.type ? EntityType[tag.type] : EntityType.Show
        }));
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
