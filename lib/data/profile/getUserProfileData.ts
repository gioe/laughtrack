import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

export async function getUserProfileData (id: number): Promise<UserProfileResponse> {
    try {
        const userData = await db.user.findUnique({
            where: {
                id: id,
            },
            select: {
                id: true,
                email: true,
                role: true,
                zipCode: true,
                emailShowNotifications: true
            },
        })
        .then((comedian) => {
            if (!comedian) return null;
            return {
                ...comedian,
            };
        });

        if (!userData) {
            throw new Error(`No user with id ${id} found`);
        }

        return {
            id: userData.id,
            email: userData.email,
            zipcode: userData.zipCode == null ? undefined : userData.zipCode,
            emailOptin: userData.emailShowNotifications,
        }
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }



};
