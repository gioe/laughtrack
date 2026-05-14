import type { ComedianLineupDTO } from "@/objects/class/comedian/comedianLineup.interface";
import { buildComedianImageUrl } from "../imageUtil";

type TaggedComedian = {
    tag?: {
        slug?: string | null;
    } | null;
};

type LineupComedian = {
    id: number;
    uuid: string;
    name: string;
    hasImage?: boolean | null;
    parentComedian?: LineupComedian | null;
    taggedComedians?: TaggedComedian[] | null;
    favoriteComedians?: unknown[] | null;
    linktree?: string | null;
    instagramAccount?: string | null;
    instagramFollowers?: number | null;
    tiktokAccount?: string | null;
    tiktokFollowers?: number | null;
    youtubeAccount?: string | null;
    youtubeFollowers?: number | null;
    website?: string | null;
    popularity?: number | null;
    _count?: {
        lineupItems?: number | null;
    } | null;
};

type LineupItem = {
    comedian: LineupComedian;
    role?: string | null;
};

export const filterAndMapLineupItems = (
    lineupItems: LineupItem[],
    userId?: string,
) => {
    // First, create a set of parent IDs that are present in the lineup
    const parentIdsInLineup = new Set(
        lineupItems
            .map((item) => {
                if (item.comedian.parentComedian == null) {
                    return item.comedian.id;
                }
            })
            .filter((item) => item !== undefined),
    );

    // Filter out children whose parents are in the lineup
    const filteredItems = lineupItems.filter((item) => {
        const parent = item.comedian.parentComedian;
        if (!parent) return true; // Keep all non-child comedians

        // Keep child only if their parent is not in the lineup
        return !parentIdsInLineup.has(parent.id);
    });

    // Map the filtered items
    return filteredItems.map((item) => mapLineupItem(item, userId));
};

const mapLineupItem = (
    item: LineupItem,
    userId?: string,
): ComedianLineupDTO => {
    const effectiveComedian = getEffectiveComedian(item.comedian);
    const isAlias = containsAliasTag(effectiveComedian.taggedComedians ?? []);
    return {
        id: effectiveComedian.id,
        uuid: effectiveComedian.uuid,
        name: effectiveComedian.name,
        imageUrl: buildComedianImageUrl(
            effectiveComedian.name,
            effectiveComedian.hasImage ?? undefined,
        ),
        hasImage: Boolean(effectiveComedian.hasImage),
        show_count: effectiveComedian._count?.lineupItems ?? undefined,
        ...(item.role ? { role: item.role } : {}),
        isFavorite: userId
            ? (item.comedian.favoriteComedians?.length ?? 0) > 0
            : false,
        isAlias,
    };
};

export const containsAliasTag = (taggedComedians: TaggedComedian[]) => {
    return taggedComedians.some((tc) => tc.tag?.slug === "alias");
};

export const getEffectiveComedian = <
    TComedian extends object,
    TParent extends object = TComedian,
>(
    comedian: TComedian & { parentComedian?: TParent | null },
): TComedian | TParent => comedian.parentComedian || comedian;
