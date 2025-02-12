import { UserProfileInterface } from "@/app/api/profile/[id]/interface";
import { db } from "@/lib/db";

export async function updateUserProfileData (slug: string, data: any): Promise<UserProfileInterface> {
    const { zipCode, emailOptin } = data

    const updatedData = await db.userProfile.update({
        where: {
            userId: slug
        },
        data: {
            zipCode: zipCode,
            emailShowNotifications: emailOptin
        },
        select: {
            id: true,
            zipCode: true,
            emailShowNotifications: true
        }
    });

    return {
        id: updatedData.id,
        zipCode: updatedData.zipCode == null ? undefined : updatedData.zipCode,
        emailOptin: updatedData.emailShowNotifications
    }
};
