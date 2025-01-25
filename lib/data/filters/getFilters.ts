import { FilterDataDTO } from "@/objects/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";

export async function getFilters(type?: string): Promise<FilterDataDTO[]> {
    try {
        const tagCategories = await db.tagCategory.findMany({
            where: type ? {
                type: type
            } : undefined,
            select: {
                id: true,
                display: true,
                value: true,
                type: true,
                tags: {
                    select: {
                        id: true,
                        display: true,
                        value: true,
                        userFacing: true
                    }
                }
            }
        });

        return tagCategories.map(category => ({
            id: category.id,
            display: category.display || '',
            value: category.value || '',
            type: category.type ? EntityType[category.type] : EntityType.Show,
            options: category.tags
                .filter(tag => tag.userFacing)
                .map(tag => ({
                    id: tag.id,
                    display: tag.display || '',
                    value: tag.value || ''
                }))
        }));
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
