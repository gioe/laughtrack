import { resolveAuth } from "@/lib/auth/resolveAuth";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";
import { NextRequest, NextResponse } from "next/server";
import { UserProfileInterface } from "./interface";

export async function PUT(req: NextRequest, { params }) {
    const [authCtx, slug] = await Promise.all([resolveAuth(req), params]);
    if (!authCtx) {
        return new NextResponse(null, { status: 401 });
    }
    if (authCtx.userId !== slug.id) {
        return new NextResponse(null, { status: 403 });
    }

    const data = await req.json();

    return updateUserProfileData(slug.id, data)
        .then((response: UserProfileInterface) =>
            NextResponse.json(
                {
                    response,
                },
                { status: 200 },
            ),
        )
        .catch((error: Error) => {
            return NextResponse.json(
                { message: error.message },
                { status: 500 },
            );
        });
}
