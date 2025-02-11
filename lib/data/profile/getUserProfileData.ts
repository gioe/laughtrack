import { UserProfileResponse } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";
import { Prisma, UserProfile } from "@prisma/client";

export async function getUserProfileData (id: string): Promise<UserProfileResponse> {
    try {
        const userProfile = await db.userProfile.findUnique({
            where: {
              userId: id
            },
            select: {
                emailShowNotifications: true,
                zipCode: true,
                user: true
            }
          });

        if (!userProfile) {
            throw new Error(`No profile for user with id ${id} found`);
        }

        return {
            zipCode: userProfile.zipCode,
            emailOptin: userProfile.emailShowNotifications,
            id: userProfile.user.id,
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
