import { db } from "@/lib/db";

export async function updateUserProfileData (email: string, zipCode: string, emailOptin: boolean): Promise<UserProfileResponse> {
    const updatedData = await db.user.update({
        where: {
            email: email
        },
        data: {
            email: email,
            zipCode: zipCode,
            emailShowNotifications: emailOptin
        },
        select: {
            id: true,
            email: true,
            zipCode: true,
            emailShowNotifications: true
        }
    });

    return {
        id: updatedData.id,
        email: updatedData.email,
        zipcode: updatedData.zipCode == null ? undefined : updatedData.zipCode,
        emailOptin: updatedData.emailShowNotifications
    }
};
