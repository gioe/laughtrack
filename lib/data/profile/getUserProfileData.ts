import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

export async function getUserProfileData (userId?: string): Promise<UserProfileInterface> {
    try {
        const userProfile = await db.userProfile.findUnique({
            where: {
              userId: userId
            },
            select: {
                emailShowNotifications: true,
                zipCode: true,
                userId: true,
                id: true,
                user: true
            }
          });

        if (!userProfile) {
            throw new Error(`No profile for user with id ${userId} found`);
        }

        return {
            zipCode: userProfile.zipCode,
            emailOptin: userProfile.emailShowNotifications,
            id: userProfile.id,
            userId: userProfile.userId,
            email: userProfile.user.email
        }
    }
    catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            throw new Error(`Database error: ${error.message}`);
        }
        throw error;
    }



};
