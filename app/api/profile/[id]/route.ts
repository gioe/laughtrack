import { auth } from "@/auth";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";
import { NextRequest, NextResponse } from "next/server";
import { UserProfileInterface } from "./interface";

export async function PUT(
    req: NextRequest,
    { params  }
) {
    const [ session, slug ] = await Promise.all([auth(), params])
    if (!session?.user) { return new NextResponse(null, { status: 401 }) }
    if (session.user.id !== slug.id) { return new NextResponse(null, { status: 403 }) }

    const data = await req.json()

    return updateUserProfileData(slug.id, data)
        .then((response: UserProfileInterface) => NextResponse.json({
            response
         }, { status: 200 }))
        .catch((error: Error) => {
            return NextResponse.json({ message: error.message }, { status: 500 })
        });
}
