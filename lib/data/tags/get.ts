import { FilterDataDTO } from "@/objects/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";
import { EntityType } from "@/objects/enum";
export async function getTags(type?: string): Promise<FilterDataDTO[]> {
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
                        value: true
                    }
                }
            }
        });

        // Transform the data to match the expected FilterDataDTO format
        const transformedData: FilterDataDTO[] = tagCategories.map(category => ({
            id: category.id,
            display: category.display || '',
            value: category.value || '',
            type: category.type ? EntityType[category.type] : EntityType.Show,
            options: category.tags.map(tag => ({
                id: tag.id,
                display: tag.display || '',
                value: tag.value || ''
            }))
        }));

        return transformedData;
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }
}
