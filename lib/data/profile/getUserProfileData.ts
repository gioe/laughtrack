import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

const USER_PROFILE_SELECT = {
    emailShowNotifications: true,
    zipCode: true,
    userid: true,
    id: true,
    user: {
        select: {
            email: true
        }
    }
} as const;

export async function getUserProfileData(userId?: string): Promise<UserProfileInterface> {
    try {
        if (!userId) {
            throw new Error('User ID is required');
        }

        const userProfile = await db.userProfile.findUnique({
            where: {
                userid: userId
            },
            select: USER_PROFILE_SELECT
        });

        if (!userProfile) {
            throw new Error(`No profile found for user with ID: ${userId}`);
        }

        return {
            zipCode: userProfile.zipCode,
            emailOptin: userProfile.emailShowNotifications,
            id: userProfile.id,
            userId: userProfile.userid,
            email: userProfile.user.email
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            console.error('Database error in getUserProfileData:', error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error('Error in getUserProfileData:', error);
            throw error;
        }
        throw new Error('An unknown error occurred while fetching user profile');
    }
}
