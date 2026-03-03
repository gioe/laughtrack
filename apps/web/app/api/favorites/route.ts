import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";
import { buildComedianImageUrl } from "@/util/imageUtil";

export async function GET(req: NextRequest) {
    try {
        const { searchParams } = new URL(req.url);
        const userId = searchParams.get('userId');

        if (!userId) {
            return NextResponse.json({ error: 'User ID is required' }, { status: 400 });
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
