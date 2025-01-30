import { getUserProfileData } from "@/lib/data/profile/getUserProfileData";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";
import { headers } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
    const headersList = await headers();
    const userId = headersList.get("user_id")
    const normalizedUserId = (!userId || userId === "undefined") ? undefined : userId;
    if (!normalizedUserId) { return NextResponse.json({ message: 'Authentication required' }, { status: 500 }) }

    return getUserProfileData(Number(normalizedUserId))
        .then((response: UserProfileResponse) => NextResponse.json({
            profile: response
         }, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}

export async function PUT(
    req: NextRequest,
) {
    const headersList = await headers();
    const userId = headersList.get("user_id")
    const normalizedUserId = (!userId || userId === "undefined") ? undefined : userId;

    if (!normalizedUserId) { return NextResponse.json({ message: 'Authentication required' }, { status: 500 }) }

    const { email, zipCode, emailOptin } = await req.json()

    return updateUserProfileData(email, zipCode, emailOptin)
        .then((response: UserProfileResponse) => NextResponse.json({
            email: response.email,
            zipcode: response.zipcode,
            emailOptin: response.emailOptin,
         }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}
