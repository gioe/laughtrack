import { resolveAuth, PROFILE_MISSING } from "@/lib/auth/resolveAuth";
import { updateUserProfileData } from "@/lib/data/profile/updateUserProfileData";
import { NextRequest, NextResponse } from "next/server";
import { UserProfileInterface } from "./interface";
import { z } from "zod";

const ProfileUpdateSchema = z
    .object({
        zipCode: z
            .string()
            .regex(/^\d{5}$/, "zipCode must be a 5-digit US zip code")
            .optional(),
        emailOptin: z.boolean().optional(),
    })
    .refine(
        (data) => data.zipCode !== undefined || data.emailOptin !== undefined,
        {
            message:
                "At least one field (zipCode or emailOptin) must be provided",
        },
    );

type ProfileUpdateInput = z.infer<typeof ProfileUpdateSchema>;

export async function PUT(
    req: NextRequest,
    { params }: { params: Promise<{ id: string }> },
) {
    const [authCtx, slug] = await Promise.all([resolveAuth(req), params]);
    if (authCtx === PROFILE_MISSING) {
        return NextResponse.json(
            {
                error: "User profile not found. Please sign out and sign in again.",
            },
            { status: 422 },
        );
    }
    if (!authCtx) {
        return new NextResponse(null, { status: 401 });
    }
    if (authCtx.userId !== slug.id) {
        return new NextResponse(null, { status: 403 });
    }

    let body: unknown;
    try {
        body = await req.json();
    } catch {
        return NextResponse.json(
            { error: "Invalid JSON body" },
            { status: 400 },
        );
    }

    const parsed = ProfileUpdateSchema.safeParse(body);
    if (!parsed.success) {
        return NextResponse.json(
            { error: parsed.error.errors[0].message },
            { status: 400 },
        );
    }

    const data: ProfileUpdateInput = parsed.data;

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
            console.error("Failed to update profile:", error);
            return NextResponse.json(
                { message: "Failed to update profile" },
                { status: 500 },
            );
        });
}
