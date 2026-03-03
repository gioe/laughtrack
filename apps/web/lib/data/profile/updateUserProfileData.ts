import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

interface UpdateProfileData {
    zipCode?: string;
    emailOptin?: boolean;
}

const USER_PROFILE_SELECT = {
    id: true,
    zipCode: true,
    emailShowNotifications: true,
    userid: true,
    user: {
        select: {
            email: true
        }
    }
} as const;

export async function updateUserProfileData(
    userId: string,
    data: UpdateProfileData
): Promise<UserProfileInterface> {
    try {
        if (!userId) {
            throw new Error('User ID is required');
        }

        const { zipCode, emailOptin } = data;

        const updatedData = await db.userProfile.update({
            where: {
                userid: userId
            },
            data: {
                zipCode: zipCode,
                emailShowNotifications: emailOptin
            },
            select: USER_PROFILE_SELECT
        });

        return {
            id: updatedData.id,
            zipCode: updatedData.zipCode ?? undefined,
            emailOptin: updatedData.emailShowNotifications,
            userId: updatedData.userid,
            email: updatedData.user.email
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            if (error.code === 'P2025') {
                throw new Error(`No profile found for user with ID: ${userId}`);
            }
            console.error('Database error in updateUserProfileData:', error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error('Error in updateUserProfileData:', error);
            throw error;
        }
        throw new Error('An unknown error occurred while updating user profile');
    }
}
