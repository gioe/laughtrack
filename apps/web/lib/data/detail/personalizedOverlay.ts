import { db } from "@/lib/db";
import type { ParameterizedRequestData } from "@/objects/interface";

const DETAIL_CACHE_PARAM_KEYS = [
    "chain",
    "club",
    "comedian",
    "distance",
    "filters",
    "fromDate",
    "page",
    "size",
    "sort",
    "toDate",
    "zip",
] as const;

type LineupFavorite = {
    uuid?: string;
    isFavorite?: boolean;
};

type FavoriteOverlayResponse = {
    data?: LineupFavorite | null;
    shows?: { lineup?: LineupFavorite[] | null }[] | null;
};

export function buildDetailCacheKey(
    tag: string,
    requestData: ParameterizedRequestData,
): string[] {
    const key = [
        tag,
        `slug:${requestData.slug ?? ""}`,
        `timezone:${requestData.timezone}`,
    ];

    for (const paramKey of DETAIL_CACHE_PARAM_KEYS) {
        const value = requestData.params[paramKey];
        if (typeof value === "string" && value.length > 0) {
            key.push(`${paramKey}:${value}`);
        }
    }

    return key;
}

export async function applyFavoriteOverlay<
    TResponse extends FavoriteOverlayResponse,
>(response: TResponse, profileId?: string): Promise<TResponse> {
    const comedianUuids = collectComedianUuids(response);

    if (!profileId || comedianUuids.length === 0) {
        return withFavoriteFlags(response, new Set());
    }

    const favorites = await db.favoriteComedian.findMany({
        where: {
            profileId,
            comedianId: { in: comedianUuids },
        },
        select: { comedianId: true },
    });

    return withFavoriteFlags(
        response,
        new Set(favorites.map((favorite) => favorite.comedianId)),
    );
}

export async function isPodcastFavorite(
    podcastId: number,
    profileId?: string,
): Promise<boolean> {
    if (!profileId) return false;

    const favorite = await db.favoritePodcast.findUnique({
        where: {
            profileId_podcastId: {
                profileId,
                podcastId,
            },
        },
        select: { id: true },
    });

    return Boolean(favorite);
}

function collectComedianUuids(response: FavoriteOverlayResponse): string[] {
    const uuids = new Set<string>();
    if (response.data?.uuid) {
        uuids.add(response.data.uuid);
    }

    for (const show of response.shows ?? []) {
        for (const lineupItem of show.lineup ?? []) {
            if (lineupItem.uuid) {
                uuids.add(lineupItem.uuid);
            }
        }
    }

    return [...uuids];
}

function withFavoriteFlags<TResponse extends FavoriteOverlayResponse>(
    response: TResponse,
    favoriteUuids: Set<string>,
): TResponse {
    return {
        ...response,
        data: response.data?.uuid
            ? {
                  ...response.data,
                  isFavorite: favoriteUuids.has(response.data.uuid),
              }
            : response.data,
        shows: response.shows?.map((show) => ({
            ...show,
            lineup: show.lineup?.map((lineupItem) =>
                lineupItem.uuid
                    ? {
                          ...lineupItem,
                          isFavorite: favoriteUuids.has(lineupItem.uuid),
                      }
                    : lineupItem,
            ),
        })),
    } as TResponse;
}
