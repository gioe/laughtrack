import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";
import { Prisma } from "@prisma/client";

interface UpdateProfileData {
    zipCode?: string;
    nearbyDistanceMiles?: number;
    emailOptin?: boolean;
    pushOptin?: boolean;
}

const USER_PROFILE_SELECT = {
    id: true,
    zipCode: true,
    nearbyDistanceMiles: true,
    emailShowNotifications: true,
    pushShowNotifications: true,
    userid: true,
    user: {
        select: {
            email: true,
        },
    },
} as const;

export async function updateUserProfileData(
    userId: string,
    data: UpdateProfileData,
): Promise<UserProfileInterface> {
    try {
        if (!userId) {
            throw new Error("User ID is required");
        }

        const { zipCode, nearbyDistanceMiles, emailOptin, pushOptin } = data;

        const updatedData = await db.userProfile.update({
            where: {
                userid: userId,
            },
            data: {
                zipCode: zipCode,
                nearbyDistanceMiles: nearbyDistanceMiles,
                emailShowNotifications: emailOptin,
                pushShowNotifications: pushOptin,
            },
            select: USER_PROFILE_SELECT,
        });

        return {
            id: updatedData.id,
            zipCode: updatedData.zipCode ?? undefined,
            nearbyDistanceMiles: updatedData.nearbyDistanceMiles,
            emailOptin: updatedData.emailShowNotifications,
            pushOptin: updatedData.pushShowNotifications,
            userId: updatedData.userid,
            email: updatedData.user.email,
        };
    } catch (error) {
        if (error instanceof Prisma.PrismaClientKnownRequestError) {
            if (error.code === "P2025") {
                throw new Error(`No profile found for user with ID: ${userId}`);
            }
            console.error("Database error in updateUserProfileData:", error);
            throw new Error(`Database error: ${error.message}`);
        }
        if (error instanceof Error) {
            console.error("Error in updateUserProfileData:", error);
            throw error;
        }
        throw new Error(
            "An unknown error occurred while updating user profile",
        );
    }
}
