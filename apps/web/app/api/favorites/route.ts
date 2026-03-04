import { auth } from "@/auth";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { buildComedianImageUrl } from "@/util/imageUtil";
import { z } from "zod";

const querySchema = z.object({
    userId: z.string().min(1),
});

export async function GET(req: NextRequest) {
    try {
        const session = await auth();
        if (!session?.profile) {
            return new NextResponse(null, { status: 401 });
        }

        const { searchParams } = new URL(req.url);
        const parsed = querySchema.safeParse({ userId: searchParams.get('userId') });

        if (!parsed.success) {
            return NextResponse.json({ error: 'userId is required and must be a non-empty string' }, { status: 400 });
        }

        const { userId } = parsed.data;

        if (session.profile.userid !== userId) {
            return new NextResponse(null, { status: 403 });
        }

        const favorites = await db.favoriteComedian.findMany({
            where: {
                user: {
                    userid: userId
                }
            },
            select: {
                comedian: {
                    select: {
                        id: true,
                        uuid: true,
                        name: true,
                        instagramAccount: true,
                        instagramFollowers: true,
                        tiktokAccount: true,
                        tiktokFollowers: true,
                        youtubeAccount: true,
                        youtubeFollowers: true,
                        website: true,
                        popularity: true,
                        linktree: true,
                    }
                }
            }
        });

        const comedians = favorites.map(favorite => ({
            ...favorite.comedian,
            imageUrl: buildComedianImageUrl(favorite.comedian.name),
            isFavorite: true,
            social_data: {
                id: favorite.comedian.id,
                instagram_account: favorite.comedian.instagramAccount,
                instagram_followers: favorite.comedian.instagramFollowers,
                tiktok_account: favorite.comedian.tiktokAccount,
                tiktok_followers: favorite.comedian.tiktokFollowers,
                youtube_account: favorite.comedian.youtubeAccount,
                youtube_followers: favorite.comedian.youtubeFollowers,
                website: favorite.comedian.website,
                popularity: favorite.comedian.popularity,
                linktree: favorite.comedian.linktree,
            }
        }));

        return NextResponse.json({ comedians });
    } catch (error) {
        console.error('Error fetching favorite comedians:', error);
        return NextResponse.json(
            { error: 'Failed to fetch favorite comedians' },
            { status: 500 }
        );
    }
}
