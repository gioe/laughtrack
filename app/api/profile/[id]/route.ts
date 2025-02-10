import { auth } from "@/auth";
import { getUserProfileData } from "@/lib/data/profile/getUserProfileData";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";
import { headers } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { UserProfileResponse } from "./interface";

export async function GET(
    request: Request,
    { params }: { params: { userId: string } }
  ) {

    const session = await auth()

    if (!session?.user) { return new NextResponse(null, { status: 401 }) }
    if (session.user.id !== Number(params.userId)) { return new NextResponse(null, { status: 403 }) }

    return getUserProfileData(Number(params.userId))
        .then((response: UserProfileResponse) => NextResponse.json({
            response
         }, { status: 200 }))
        .catch((error: Error) => NextResponse.json({ message: error.message }, { status: 500 }));
}

export async function PUT(
    req: NextRequest,
    { params }: { params: { userId: string } }

) {
    const session = await auth()

    if (!session?.user) { return new NextResponse(null, { status: 401 }) }
    if (session.user.id !== Number(params.userId)) { return new NextResponse(null, { status: 403 }) }

    const { email, zipCode, emailOptin } = await req.json()

    return updateUserProfileData(email, zipCode, emailOptin)
        .then((response: UserProfileResponse) => NextResponse.json({
            response
         }, { status: 200 }))
        .catch((error: Error) => {
            console.log(error)
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
