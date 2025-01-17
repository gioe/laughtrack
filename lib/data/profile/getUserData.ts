import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

const getUserData = (id: number) => {
    try {
        return db.user.findUnique({
            where: {
                id: id,
            },
            select: {
                id: true,
                email: true,
                role: true,
                zipCode: true,
            },
        });
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }



};
